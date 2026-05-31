import { useState, useEffect, useCallback } from 'react';
import { Settings, Plus, Trash2, Edit2, Save, X, Eye, EyeOff, RotateCw, Palette, Target, Star, Gift, TrendingUp } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useRealtime } from '../hooks/useRealtime';
import Modal from '../components/ui/Modal';

interface WheelPrize {
  id: string;
  name: string;
  description: string;
  value: number;
  currency: 'SYP' | 'USD';
  probability: number;
  color: string;
  icon: string;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

interface WheelSettings {
  id: string;
  spin_duration: number;
  min_spins: number;
  max_spins: number;
  cost_per_spin: number;
  cost_currency: 'SYP' | 'USD';
  auto_spin_enabled: boolean;
  sound_enabled: boolean;
  animation_speed: number;
  background_color: string;
  pointer_color: string;
  center_color: string;
  border_color: string;
  created_at: string;
  updated_at: string;
}

interface WheelStats {
  total_spins: number;
  today_spins: number;
  total_wins: number;
  today_wins: number;
  total_payout: number;
  today_payout: number;
  average_win_rate: number;
  most_won_prize: string;
  least_won_prize: string;
  prize_distribution: Array<{
    prize_id: string;
    prize_name: string;
    times_won: number;
    total_payout: number;
    win_rate: number;
  }>;
}

const DEFAULT_COLORS = [
  '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e',
  '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1',
  '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e'
];

const ICONS = [
  '🎁', '🎯', '⭐', '💎', '🏆', '🎪', '🎭', '🎨', '🎬', '🎮',
  '🎲', '🎰', '🎳', '🎯', '🎪', '🎭', '🎨', '🎬', '🎮', '🎲'
];

export default function WheelConfigPage() {
  const { theme, language, exchangeRate } = useApp();
  const isDark = theme === 'dark';

  const [prizes, setPrizes] = useState<WheelPrize[]>([]);
  const [settings, setSettings] = useState<WheelSettings | null>(null);
  const [stats, setStats] = useState<WheelStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingPrize, setEditingPrize] = useState<WheelPrize | null>(null);
  const [showPrizeModal, setShowPrizeModal] = useState(false);
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [showIconPicker, setShowIconPicker] = useState(false);
  const [selectedColorIndex, setSelectedColorIndex] = useState(0);
  const [selectedIconIndex, setSelectedIconIndex] = useState(0);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    value: '',
    currency: 'SYP' as 'SYP' | 'USD',
    probability: '',
    color: DEFAULT_COLORS[0],
    icon: ICONS[0],
    is_active: true
  });

  const loadPrizes = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('wheel_prizes')
        .select('*')
        .order('sort_order', { ascending: true });

      if (error) throw error;
      setPrizes(data as WheelPrize[]);
    } catch (error) {
      console.error('[WheelConfigPage] Error loading prizes:', error);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('wheel_settings')
        .select('*')
        .maybeSingle();

      if (error && error.code !== 'PGRST116') throw error;
      
      if (data) {
        setSettings(data as WheelSettings);
      } else {
        // Create default settings
        const defaultSettings = {
          spin_duration: 3000,
          min_spins: 1,
          max_spins: 10,
          cost_per_spin: 1000,
          cost_currency: 'SYP',
          auto_spin_enabled: false,
          sound_enabled: true,
          animation_speed: 1,
          background_color: '#1f2937',
          pointer_color: '#ef4444',
          center_color: '#f59e0b',
          border_color: '#f59e0b'
        };

        const { data: newSettings, error: insertError } = await supabase
          .from('wheel_settings')
          .insert([defaultSettings])
          .select()
          .single();

        if (insertError) throw insertError;
        setSettings(newSettings as WheelSettings);
      }
    } catch (error) {
      console.error('[WheelConfigPage] Error loading settings:', error);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const [
        totalSpinsRes,
        todaySpinsRes,
        totalWinsRes,
        todayWinsRes,
        payoutRes,
        todayPayoutRes,
        distributionRes
      ] = await Promise.all([
        supabase.from('wheel_games').select('id'),
        supabase.from('wheel_games').select('id').gte('created_at', today.toISOString()),
        supabase.from('wheel_games').select('id').eq('status', 'won'),
        supabase.from('wheel_games').select('id').eq('status', 'won').gte('created_at', today.toISOString()),
        supabase.from('wheel_games').select('prize_value, currency').eq('status', 'won'),
        supabase.from('wheel_games').select('prize_value, currency').eq('status', 'won').gte('created_at', today.toISOString()),
        supabase.from('wheel_game_stats').select('*').order('times_won', { ascending: false })
      ]);

      const totalSpins = totalSpinsRes.data?.length || 0;
      const todaySpins = todaySpinsRes.data?.length || 0;
      const totalWins = totalWinsRes.data?.length || 0;
      const todayWins = todayWinsRes.data?.length || 0;

      const calculatePayout = (data: any[]) => {
        return data.reduce((sum, item) => {
          const value = Number(item.prize_value);
          return sum + (item.currency === 'USD' ? value * exchangeRate : value);
        }, 0);
      };

      const totalPayout = calculatePayout(payoutRes.data || []);
      const todayPayout = calculatePayout(todayPayoutRes.data || []);

      const averageWinRate = totalSpins > 0 ? (totalWins / totalSpins) * 100 : 0;

      const distribution = (distributionRes.data || []).map((item: any) => ({
        ...item,
        win_rate: totalSpins > 0 ? (item.times_won / totalSpins) * 100 : 0
      }));

      setStats({
        total_spins: totalSpins,
        today_spins: todaySpins,
        total_wins: totalWins,
        today_wins: todayWins,
        total_payout: totalPayout,
        today_payout: todayPayout,
        average_win_rate,
        most_won_prize: distribution[0]?.prize_name || '',
        least_won_prize: distribution[distribution.length - 1]?.prize_name || '',
        prize_distribution: distribution
      });
    } catch (error) {
      console.error('[WheelConfigPage] Error loading stats:', error);
    }
  }, [exchangeRate]);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadPrizes(), loadSettings(), loadStats()]).finally(() => {
      setLoading(false);
    });
  }, [loadPrizes, loadSettings, loadStats]);

  useRealtime({
    table: 'wheel_prizes',
    onInsert: () => loadPrizes(),
    onUpdate: () => loadPrizes(),
    onDelete: () => loadPrizes()
  });

  useRealtime({
    table: 'wheel_settings',
    onUpdate: () => loadSettings()
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      value: '',
      currency: 'SYP',
      probability: '',
      color: DEFAULT_COLORS[0],
      icon: ICONS[0],
      is_active: true
    });
    setEditingPrize(null);
  };

  const openPrizeModal = (prize?: WheelPrize) => {
    if (prize) {
      setFormData({
        name: prize.name,
        description: prize.description,
        value: prize.value.toString(),
        currency: prize.currency,
        probability: prize.probability.toString(),
        color: prize.color,
        icon: prize.icon,
        is_active: prize.is_active
      });
      setEditingPrize(prize);
    } else {
      resetForm();
    }
    setShowPrizeModal(true);
  };

  const savePrize = async () => {
    try {
      const prizeData = {
        name: formData.name,
        description: formData.description,
        value: Number(formData.value),
        currency: formData.currency,
        probability: Number(formData.probability),
        color: formData.color,
        icon: formData.icon,
        is_active: formData.is_active,
        sort_order: editingPrize ? editingPrize.sort_order : prizes.length
      };

      if (editingPrize) {
        const { error } = await supabase
          .from('wheel_prizes')
          .update(prizeData)
          .eq('id', editingPrize.id);

        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('wheel_prizes')
          .insert([prizeData]);

        if (error) throw error;
      }

      setShowPrizeModal(false);
      resetForm();
      loadPrizes();
    } catch (error) {
      console.error('[WheelConfigPage] Error saving prize:', error);
    }
  };

  const deletePrize = async (prizeId: string) => {
    if (!confirm(language === 'ar' ? 'هل أنت متأكد من حذف هذه الجائزة؟' : 'Are you sure you want to delete this prize?')) {
      return;
    }

    try {
      const { error } = await supabase
        .from('wheel_prizes')
        .delete()
        .eq('id', prizeId);

      if (error) throw error;
      loadPrizes();
    } catch (error) {
      console.error('[WheelConfigPage] Error deleting prize:', error);
    }
  };

  const togglePrizeStatus = async (prize: WheelPrize) => {
    try {
      const { error } = await supabase
        .from('wheel_prizes')
        .update({ is_active: !prize.is_active })
        .eq('id', prize.id);

      if (error) throw error;
      loadPrizes();
    } catch (error) {
      console.error('[WheelConfigPage] Error toggling prize status:', error);
    }
  };

  const saveSettings = async () => {
    if (!settings) return;

    try {
      const { error } = await supabase
        .from('wheel_settings')
        .update(settings)
        .eq('id', settings.id);

      if (error) throw error;
    } catch (error) {
      console.error('[WheelConfigPage] Error saving settings:', error);
    }
  };

  const reorderPrizes = async (fromIndex: number, toIndex: number) => {
    const newPrizes = [...prizes];
    const [movedPrize] = newPrizes.splice(fromIndex, 1);
    newPrizes.splice(toIndex, 0, movedPrize);

    // Update sort_order for all prizes
    const updates = newPrizes.map((prize, index) => ({
      id: prize.id,
      sort_order: index
    }));

    try {
      const { error } = await supabase
        .from('wheel_prizes')
        .upsert(updates, { onConflict: 'id' });

      if (error) throw error;
      loadPrizes();
    } catch (error) {
      console.error('[WheelConfigPage] Error reordering prizes:', error);
    }
  };

  const fmt = (n: number) => new Intl.NumberFormat(language === 'ar' ? 'ar-SY' : 'en-US').format(Math.round(n));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-2">
          <RotateCw className="w-5 h-5 animate-spin" />
          <span className={isDark ? 'text-slate-400' : 'text-slate-600'}>
            {language === 'ar' ? 'جاري التحميل...' : 'Loading...'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {language === 'ar' ? 'إعدادات العجلة' : 'Wheel Configuration'}
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            {language === 'ar' ? 'تخصيص العجلة والجوائز' : 'Customize wheel and prizes'}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowStatsModal(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all
              ${isDark ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'}
            `}
          >
            <TrendingUp className="w-4 h-4" />
            {language === 'ar' ? 'الإحصائيات' : 'Statistics'}
          </button>
          <button
            onClick={() => openPrizeModal()}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all
              ${isDark ? 'bg-emerald-600 text-white hover:bg-emerald-700' : 'bg-emerald-500 text-white hover:bg-emerald-600'}
            `}
          >
            <Plus className="w-4 h-4" />
            {language === 'ar' ? 'إضافة جائزة' : 'Add Prize'}
          </button>
        </div>
      </div>

      {/* Settings */}
      {settings && (
        <div className={`rounded-xl border p-6 ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
          <h2 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {language === 'ar' ? 'الإعدادات العامة' : 'General Settings'}
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'مدة الدوران (مللي ثانية)' : 'Spin Duration (ms)'}
              </label>
              <input
                type="number"
                value={settings.spin_duration}
                onChange={(e) => setSettings({ ...settings, spin_duration: Number(e.target.value) })}
                className={`w-full px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
              />
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'تكلفة الدوران' : 'Cost Per Spin'}
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={settings.cost_per_spin}
                  onChange={(e) => setSettings({ ...settings, cost_per_spin: Number(e.target.value) })}
                  className={`flex-1 px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                />
                <select
                  value={settings.cost_currency}
                  onChange={(e) => setSettings({ ...settings, cost_currency: e.target.value as 'SYP' | 'USD' })}
                  className={`px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                >
                  <option value="SYP">ل.س</option>
                  <option value="USD">$</option>
                </select>
              </div>
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'سرعة الرسوم المتحركة' : 'Animation Speed'}
              </label>
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={settings.animation_speed}
                onChange={(e) => setSettings({ ...settings, animation_speed: Number(e.target.value) })}
                className="w-full"
              />
              <div className="flex justify-between text-xs mt-1">
                <span className={isDark ? 'text-slate-400' : 'text-slate-600'}>0.5x</span>
                <span className={isDark ? 'text-slate-400' : 'text-slate-600'}>{settings.animation_speed}x</span>
                <span className={isDark ? 'text-slate-400' : 'text-slate-600'}>2x</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto_spin"
                checked={settings.auto_spin_enabled}
                onChange={(e) => setSettings({ ...settings, auto_spin_enabled: e.target.checked })}
                className="rounded"
              />
              <label htmlFor="auto_spin" className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'تفعيل الدوران التلقائي' : 'Enable Auto Spin'}
              </label>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="sound"
                checked={settings.sound_enabled}
                onChange={(e) => setSettings({ ...settings, sound_enabled: e.target.checked })}
                className="rounded"
              />
              <label htmlFor="sound" className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'تفعيل الأصوات' : 'Enable Sounds'}
              </label>
            </div>

            <div className="flex items-center gap-2">
              <label className={`text-sm font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'الحد الأدنى للدورانات' : 'Min Spins'}
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.min_spins}
                onChange={(e) => setSettings({ ...settings, min_spins: Number(e.target.value) })}
                className={`w-20 px-2 py-1 rounded border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
              />
              <label className={`text-sm font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'الحد الأقصى' : 'Max'}
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.max_spins}
                onChange={(e) => setSettings({ ...settings, max_spins: Number(e.target.value) })}
                className={`w-20 px-2 py-1 rounded border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
              />
            </div>
          </div>

          {/* Color Settings */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <h3 className={`text-md font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {language === 'ar' ? 'إعدادات الألوان' : 'Color Settings'}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'لون الخلفية' : 'Background Color'}
                </label>
                <input
                  type="color"
                  value={settings.background_color}
                  onChange={(e) => setSettings({ ...settings, background_color: e.target.value })}
                  className="w-full h-10 rounded cursor-pointer"
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'لون المؤشر' : 'Pointer Color'}
                </label>
                <input
                  type="color"
                  value={settings.pointer_color}
                  onChange={(e) => setSettings({ ...settings, pointer_color: e.target.value })}
                  className="w-full h-10 rounded cursor-pointer"
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'لون المركز' : 'Center Color'}
                </label>
                <input
                  type="color"
                  value={settings.center_color}
                  onChange={(e) => setSettings({ ...settings, center_color: e.target.value })}
                  className="w-full h-10 rounded cursor-pointer"
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'لون الحدود' : 'Border Color'}
                </label>
                <input
                  type="color"
                  value={settings.border_color}
                  onChange={(e) => setSettings({ ...settings, border_color: e.target.value })}
                  className="w-full h-10 rounded cursor-pointer"
                />
              </div>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-slate-200">
            <button
              onClick={saveSettings}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
                ${isDark ? 'bg-emerald-600 text-white hover:bg-emerald-700' : 'bg-emerald-500 text-white hover:bg-emerald-600'}
              `}
            >
              <Save className="w-4 h-4" />
              {language === 'ar' ? 'حفظ الإعدادات' : 'Save Settings'}
            </button>
          </div>
        </div>
      )}

      {/* Prizes List */}
      <div className={`rounded-xl border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="p-4 border-b border-slate-200">
          <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {language === 'ar' ? 'قائمة الجوائز' : 'Prizes List'}
          </h2>
        </div>

        <div className="divide-y divide-slate-200">
          {prizes.length === 0 ? (
            <div className="p-8 text-center">
              <Gift className={`w-12 h-12 mx-auto mb-4 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
              <p className={isDark ? 'text-slate-400' : 'text-slate-600'}>
                {language === 'ar' ? 'لا توجد جوائز حالياً' : 'No prizes available'}
              </p>
              <button
                onClick={() => openPrizeModal()}
                className={`mt-4 px-4 py-2 rounded-lg font-medium transition-all
                  ${isDark ? 'bg-emerald-600 text-white hover:bg-emerald-700' : 'bg-emerald-500 text-white hover:bg-emerald-600'}
                `}
              >
                {language === 'ar' ? 'إضافة أول جائزة' : 'Add First Prize'}
              </button>
            </div>
          ) : (
            prizes.map((prize, index) => (
              <div key={prize.id} className={`p-4 ${isDark ? 'hover:bg-slate-700/30' : 'hover:bg-slate-50'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={() => index > 0 && reorderPrizes(index, index - 1)}
                        disabled={index === 0}
                        className={`p-1 rounded ${index === 0 ? 'text-slate-400 cursor-not-allowed' : 'text-slate-600 hover:bg-slate-200'}`}
                      >
                        ▲
                      </button>
                      <button
                        onClick={() => index < prizes.length - 1 && reorderPrizes(index, index + 1)}
                        disabled={index === prizes.length - 1}
                        className={`p-1 rounded ${index === prizes.length - 1 ? 'text-slate-400 cursor-not-allowed' : 'text-slate-600 hover:bg-slate-200'}`}
                      >
                        ▼
                      </button>
                    </div>
                    
                    <div className="w-12 h-12 rounded-full flex items-center justify-center text-2xl border-2"
                         style={{ backgroundColor: prize.color + '20', borderColor: prize.color }}>
                      {prize.icon}
                    </div>
                    
                    <div>
                      <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {prize.name}
                      </h3>
                      <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                        {prize.description}
                      </p>
                      <div className="flex items-center gap-4 mt-1">
                        <span className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          {fmt(prize.value)} {prize.currency}
                        </span>
                        <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                          {prize.probability}% {language === 'ar' ? 'احتمال' : 'probability'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => togglePrizeStatus(prize)}
                      className={`p-2 rounded-lg transition-all ${
                        prize.is_active
                          ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {prize.is_active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </button>
                    
                    <button
                      onClick={() => openPrizeModal(prize)}
                      className={`p-2 rounded-lg transition-all ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={() => deletePrize(prize.id)}
                      className={`p-2 rounded-lg transition-all ${isDark ? 'bg-red-900/20 text-red-400 hover:bg-red-900/30' : 'bg-red-100 text-red-600 hover:bg-red-200'}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Prize Modal */}
      {showPrizeModal && (
        <Modal onClose={() => setShowPrizeModal(false)}>
          <div className="space-y-4">
            <h3 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {editingPrize ? (language === 'ar' ? 'تعديل الجائزة' : 'Edit Prize') : (language === 'ar' ? 'إضافة جائزة جديدة' : 'Add New Prize')}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'اسم الجائزة' : 'Prize Name'}
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className={`w-full px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                  placeholder={language === 'ar' ? 'أدخل اسم الجائزة' : 'Enter prize name'}
                />
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'القيمة' : 'Value'}
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={formData.value}
                    onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                    className={`flex-1 px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                    placeholder={language === 'ar' ? 'أدخل القيمة' : 'Enter value'}
                  />
                  <select
                    value={formData.currency}
                    onChange={(e) => setFormData({ ...formData, currency: e.target.value as 'SYP' | 'USD' })}
                    className={`px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                  >
                    <option value="SYP">ل.س</option>
                    <option value="USD">$</option>
                  </select>
                </div>
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'الاحتمال (%)' : 'Probability (%)'}
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={formData.probability}
                  onChange={(e) => setFormData({ ...formData, probability: e.target.value })}
                  className={`w-full px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                  placeholder={language === 'ar' ? 'أدخل الاحتمال' : 'Enter probability'}
                />
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'الوصف' : 'Description'}
                </label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className={`w-full px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                  placeholder={language === 'ar' ? 'أدخل الوصف' : 'Enter description'}
                />
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'اللون' : 'Color'}
                </label>
                <div className="flex gap-2">
                  <div
                    className="w-10 h-10 rounded cursor-pointer border-2"
                    style={{ backgroundColor: formData.color }}
                    onClick={() => setShowColorPicker(true)}
                  />
                  <input
                    type="text"
                    value={formData.color}
                    onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                    className={`flex-1 px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                  />
                </div>
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {language === 'ar' ? 'الأيقونة' : 'Icon'}
                </label>
                <div className="flex gap-2">
                  <div
                    className="w-10 h-10 rounded cursor-pointer border-2 flex items-center justify-center text-xl"
                    onClick={() => setShowIconPicker(true)}
                  >
                    {formData.icon}
                  </div>
                  <input
                    type="text"
                    value={formData.icon}
                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                    className={`flex-1 px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded"
              />
              <label htmlFor="active" className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {language === 'ar' ? 'جائزة نشطة' : 'Active Prize'}
              </label>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowPrizeModal(false)}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                {language === 'ar' ? 'إلغاء' : 'Cancel'}
              </button>
              <button
                onClick={savePrize}
                disabled={!formData.name || !formData.value || !formData.probability}
                className={`px-4 py-2 rounded-lg font-medium transition-all
                  ${!formData.name || !formData.value || !formData.probability
                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                    : 'bg-emerald-500 text-white hover:bg-emerald-600'
                  }
                `}
              >
                {editingPrize ? (language === 'ar' ? 'تحديث' : 'Update') : (language === 'ar' ? 'إضافة' : 'Add')}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Color Picker Modal */}
      {showColorPicker && (
        <Modal onClose={() => setShowColorPicker(false)}>
          <div className="space-y-4">
            <h3 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {language === 'ar' ? 'اختر اللون' : 'Choose Color'}
            </h3>
            <div className="grid grid-cols-6 gap-2">
              {DEFAULT_COLORS.map((color, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setFormData({ ...formData, color });
                    setSelectedColorIndex(index);
                    setShowColorPicker(false);
                  }}
                  className={`w-12 h-12 rounded-lg border-2 transition-all ${
                    selectedColorIndex === index ? 'border-blue-500 scale-110' : 'border-slate-300'
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>
        </Modal>
      )}

      {/* Icon Picker Modal */}
      {showIconPicker && (
        <Modal onClose={() => setShowIconPicker(false)}>
          <div className="space-y-4">
            <h3 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {language === 'ar' ? 'اختر الأيقونة' : 'Choose Icon'}
            </h3>
            <div className="grid grid-cols-5 gap-2">
              {ICONS.map((icon, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setFormData({ ...formData, icon });
                    setSelectedIconIndex(index);
                    setShowIconPicker(false);
                  }}
                  className={`w-12 h-12 rounded-lg border-2 text-2xl transition-all ${
                    selectedIconIndex === index ? 'border-blue-500 scale-110' : 'border-slate-300'
                  } ${isDark ? 'bg-slate-700' : 'bg-white'}`}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>
        </Modal>
      )}

      {/* Stats Modal */}
      {showStatsModal && stats && (
        <Modal onClose={() => setShowStatsModal(false)} large>
          <div className="space-y-6">
            <h3 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {language === 'ar' ? 'إحصائيات العجلة' : 'Wheel Statistics'}
            </h3>

            {/* Overview Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className={`p-4 rounded-lg ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
                <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'إجمالي الدورانات' : 'Total Spins'}
                </p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {fmt(stats.total_spins)}
                </p>
                <p className={`text-xs ${stats.today_spins > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                  +{fmt(stats.today_spins)} {language === 'ar' ? 'اليوم' : 'today'}
                </p>
              </div>

              <div className={`p-4 rounded-lg ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
                <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'إجمالي الفوز' : 'Total Wins'}
                </p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {fmt(stats.total_wins)}
                </p>
                <p className={`text-xs ${stats.today_wins > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                  +{fmt(stats.today_wins)} {language === 'ar' ? 'اليوم' : 'today'}
                </p>
              </div>

              <div className={`p-4 rounded-lg ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
                <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'إجمالي المدفوعات' : 'Total Payout'}
                </p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {fmt(stats.total_payout)} ل.س
                </p>
                <p className={`text-xs ${stats.today_payout > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                  +{fmt(stats.today_payout)} ل.س {language === 'ar' ? 'اليوم' : 'today'}
                </p>
              </div>

              <div className={`p-4 rounded-lg ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
                <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'معدل الفوز' : 'Win Rate'}
                </p>
                <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {stats.average_win_rate.toFixed(1)}%
                </p>
                <p className={`text-xs text-slate-400`}>
                  {language === 'ar' ? 'متوسط' : 'Average'}
                </p>
              </div>
            </div>

            {/* Prize Distribution */}
            <div>
              <h4 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                {language === 'ar' ? 'توزيع الجوائز' : 'Prize Distribution'}
              </h4>
              <div className="space-y-2">
                {stats.prize_distribution.map((item) => (
                  <div key={item.prize_id} className={`flex items-center justify-between p-3 rounded-lg ${isDark ? 'bg-slate-700/30' : 'bg-slate-50'}`}>
                    <div>
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {item.prize_name}
                      </p>
                      <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                        {language === 'ar' ? 'فاز' : 'Won'} {item.times_won} {language === 'ar' ? 'مرة' : 'times'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {fmt(item.total_payout)} ل.س
                      </p>
                      <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                        {item.win_rate.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
