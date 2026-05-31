import { useState, useEffect, useCallback } from 'react';
import { RotateCw, Play, Pause, Settings, Gift, TrendingUp, Users, Clock, DollarSign, Star, Trophy, Target } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useRealtime } from '../hooks/useRealtime';
import Modal from '../components/ui/Modal';
import SparklineChart from '../components/charts/SparklineChart';

interface WheelGame {
  id: string;
  player_id: string;
  player_name: string;
  prize_id: string;
  prize_name: string;
  prize_value: number;
  currency: 'SYP' | 'USD';
  status: 'playing' | 'won' | 'lost';
  spin_result: number;
  created_at: string;
  completed_at?: string;
}

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
}

interface WheelStats {
  totalGames: number;
  todayGames: number;
  totalPrizes: number;
  todayPrizes: number;
  totalValue: number;
  todayValue: number;
  activePlayers: number;
  topPrizes: WheelPrize[];
  recentGames: WheelGame[];
  hourlyStats: Array<{
    hour: string;
    games: number;
    prizes: number;
    value: number;
  }>;
}

export default function WheelPage() {
  const { theme, language, exchangeRate } = useApp();
  const isDark = theme === 'dark';

  const [games, setGames] = useState<WheelGame[]>([]);
  const [prizes, setPrizes] = useState<WheelPrize[]>([]);
  const [stats, setStats] = useState<WheelStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSpinning, setIsSpinning] = useState(false);
  const [selectedPrize, setSelectedPrize] = useState<WheelPrize | null>(null);
  const [showPrizeModal, setShowPrizeModal] = useState(false);
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [currentSpin, setCurrentSpin] = useState(0);
  const [spinSpeed, setSpinSpeed] = useState(0);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState<'all' | 'playing' | 'won' | 'lost'>('all');
  const [searchPlayer, setSearchPlayer] = useState('');

  const PAGE_SIZE = 20;

  const loadGames = useCallback(async () => {
    setLoading(true);
    try {
      let q = supabase.from('wheel_games').select('*', { count: 'exact' });

      if (filterStatus !== 'all') {
        q = q.eq('status', filterStatus);
      }

      if (searchPlayer) {
        q = q.or(`player_name.ilike.%${searchPlayer}%`);
      }

      q = q.order('created_at', { ascending: false })
        .range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);

      const { data, count, error } = await q;

      if (error) throw error;

      setGames(data as WheelGame[]);
      setTotal(count || 0);
    } catch (error) {
      console.error('[WheelPage] Error loading games:', error);
    } finally {
      setLoading(false);
    }
  }, [page, filterStatus, searchPlayer]);

  const loadPrizes = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from('wheel_prizes')
        .select('*')
        .eq('is_active', true)
        .order('sort_order', { ascending: true });

      if (error) throw error;

      setPrizes(data as WheelPrize[]);
    } catch (error) {
      console.error('[WheelPage] Error loading prizes:', error);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const [
        gamesRes,
        todayGamesRes,
        prizesRes,
        todayPrizesRes,
        valueRes,
        todayValueRes,
        activePlayersRes,
        topPrizesRes,
        recentGamesRes
      ] = await Promise.all([
        supabase.from('wheel_games').select('id').eq('status', 'won'),
        supabase.from('wheel_games').select('id').eq('status', 'won').gte('created_at', today.toISOString()),
        supabase.from('wheel_games').select('id').eq('status', 'won'),
        supabase.from('wheel_games').select('id').eq('status', 'won').gte('created_at', today.toISOString()),
        supabase.from('wheel_games').select('prize_value, currency').eq('status', 'won'),
        supabase.from('wheel_games').select('prize_value, currency').eq('status', 'won').gte('created_at', today.toISOString()),
        supabase.from('wheel_games').select('player_id').neq('status', 'lost'),
        supabase.from('wheel_prizes').select('*').eq('is_active', true).order('value', { ascending: false }).limit(5),
        supabase.from('wheel_games').select('*').order('created_at', { ascending: false }).limit(10)
      ]);

      const totalGames = gamesRes.data?.length || 0;
      const todayGames = todayGamesRes.data?.length || 0;
      const totalPrizes = prizesRes.data?.length || 0;
      const todayPrizes = todayPrizesRes.data?.length || 0;

      const calculateValue = (data: any[]) => {
        return data.reduce((sum, item) => {
          const value = Number(item.prize_value);
          return sum + (item.currency === 'USD' ? value * exchangeRate : value);
        }, 0);
      };

      const totalValue = calculateValue(valueRes.data || []);
      const todayValue = calculateValue(todayValueRes.data || []);

      const activePlayers = new Set((activePlayersRes.data || []).map((g: any) => g.player_id)).size;

      // Generate hourly stats for last 24 hours
      const hourlyStats = [];
      for (let i = 23; i >= 0; i--) {
        const hour = new Date();
        hour.setHours(hour.getHours() - i, 0, 0, 0);
        const nextHour = new Date(hour);
        nextHour.setHours(nextHour.getHours() + 1);

        const { data: hourGames } = await supabase
          .from('wheel_games')
          .select('prize_value, currency, status')
          .gte('created_at', hour.toISOString())
          .lt('created_at', nextHour.toISOString());

        const games = hourGames?.length || 0;
        const prizes = hourGames?.filter(g => g.status === 'won').length || 0;
        const value = calculateValue(hourGames?.filter(g => g.status === 'won') || []);

        hourlyStats.push({
          hour: hour.toLocaleTimeString(language === 'ar' ? 'ar-SA' : 'en-US', { hour: '2-digit', minute: '2-digit' }),
          games,
          prizes,
          value
        });
      }

      setStats({
        totalGames,
        todayGames,
        totalPrizes,
        todayPrizes,
        totalValue,
        todayValue,
        activePlayers,
        topPrizes: topPrizesRes.data as WheelPrize[],
        recentGames: recentGamesRes.data as WheelGame[],
        hourlyStats
      });
    } catch (error) {
      console.error('[WheelPage] Error loading stats:', error);
    }
  }, [language, exchangeRate]);

  useEffect(() => {
    loadGames();
    loadPrizes();
    loadStats();
  }, [loadGames, loadPrizes, loadStats]);

  useRealtime({
    table: 'wheel_games',
    onInsert: () => {
      loadGames();
      loadStats();
    },
    onUpdate: () => {
      loadGames();
      loadStats();
    }
  });

  useRealtime({
    table: 'wheel_prizes',
    onUpdate: () => {
      loadPrizes();
      loadStats();
    }
  });

  const simulateSpin = () => {
    if (isSpinning || prizes.length === 0) return;

    setIsSpinning(true);
    setCurrentSpin(0);
    setSpinSpeed(20);

    const duration = 3000 + Math.random() * 2000;
    const finalPrize = prizes[Math.floor(Math.random() * prizes.length)];
    const finalRotation = Math.floor(Math.random() * 360) + 720; // At least 2 full rotations

    let startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function for smooth deceleration
      const easeOut = 1 - Math.pow(1 - progress, 3);
      
      const currentRotation = finalRotation * easeOut;
      setCurrentSpin(currentRotation);
      setSpinSpeed(20 * (1 - easeOut));

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setIsSpinning(false);
        setSelectedPrize(finalPrize);
        setShowPrizeModal(true);
        setSpinSpeed(0);
      }
    };

    requestAnimationFrame(animate);
  };

  const fmt = (n: number) => new Intl.NumberFormat(language === 'ar' ? 'ar-SY' : 'en-US').format(Math.round(n));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {language === 'ar' ? 'عجلة الحظ' : 'Wheel of Fortune'}
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            {language === 'ar' ? 'إدارة لعبة العجلة والجوائز' : 'Manage wheel game and prizes'}
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
            onClick={simulateSpin}
            disabled={isSpinning || prizes.length === 0}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all
              ${isSpinning || prizes.length === 0
                ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                : 'bg-emerald-500 text-white hover:bg-emerald-600'
              }
            `}
          >
            <RotateCw className={`w-4 h-4 ${isSpinning ? 'animate-spin' : ''}`} />
            {isSpinning ? (language === 'ar' ? 'يدور...' : 'Spinning...') : (language === 'ar' ? 'دوران' : 'Spin')}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className={`rounded-xl p-4 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'إجمالي الألعاب' : 'Total Games'}
                </p>
                <p className={`text-xl font-bold mt-1 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {fmt(stats.totalGames)}
                </p>
                <p className={`text-xs mt-1 ${stats.todayGames > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                  +{fmt(stats.todayGames)} {language === 'ar' ? 'اليوم' : 'today'}
                </p>
              </div>
              <Target className={`w-8 h-8 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
            </div>
          </div>

          <div className={`rounded-xl p-4 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'الجوائز الفاز بها' : 'Prizes Won'}
                </p>
                <p className={`text-xl font-bold mt-1 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {fmt(stats.totalPrizes)}
                </p>
                <p className={`text-xs mt-1 ${stats.todayPrizes > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                  +{fmt(stats.todayPrizes)} {language === 'ar' ? 'اليوم' : 'today'}
                </p>
              </div>
              <Trophy className={`w-8 h-8 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
            </div>
          </div>

          <div className={`rounded-xl p-4 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'إجمالي القيمة' : 'Total Value'}
                </p>
                <p className={`text-xl font-bold mt-1 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {fmt(stats.totalValue)} ل.س
                </p>
                <p className={`text-xs mt-1 ${stats.todayValue > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                  +{fmt(stats.todayValue)} ل.س {language === 'ar' ? 'اليوم' : 'today'}
                </p>
              </div>
              <DollarSign className={`w-8 h-8 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
            </div>
          </div>

          <div className={`rounded-xl p-4 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {language === 'ar' ? 'لاعبين نشطين' : 'Active Players'}
                </p>
                <p className={`text-xl font-bold mt-1 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {fmt(stats.activePlayers)}
                </p>
                <p className={`text-xs mt-1 text-slate-400`}>
                  {language === 'ar' ? 'فترة 24 ساعة' : 'Last 24h'}
                </p>
              </div>
              <Users className={`w-8 h-8 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
            </div>
          </div>
        </div>
      )}

      {/* Wheel Visualization */}
      <div className={`rounded-xl border p-6 ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-col items-center">
          <div className="relative w-64 h-64 mb-6">
            {/* Wheel */}
            <div
              className="absolute inset-0 rounded-full border-4 border-amber-500 shadow-2xl"
              style={{
                background: `conic-gradient(${prizes.map((prize, index) => 
                  `${prize.color} ${index * (360 / prizes.length)}deg ${(index + 1) * (360 / prizes.length)}deg`
                ).join(', ')})`,
                transform: `rotate(${currentSpin}deg)`,
                transition: isSpinning ? 'none' : 'transform 0.3s ease-out'
              }}
            >
              {/* Prize labels */}
              {prizes.map((prize, index) => (
                <div
                  key={prize.id}
                  className="absolute text-white font-bold text-sm"
                  style={{
                    top: '50%',
                    left: '50%',
                    transform: `rotate(${index * (360 / prizes.length) + (360 / prizes.length) / 2}deg) translateY(-100px)`,
                    transformOrigin: 'center bottom'
                  }}
                >
                  {prize.icon}
                </div>
              ))}
            </div>
            
            {/* Center circle */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-amber-600 rounded-full border-4 border-amber-700 flex items-center justify-center shadow-lg">
              <Star className="w-8 h-8 text-white" />
            </div>

            {/* Pointer */}
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-2">
              <div className="w-0 h-0 border-l-8 border-r-8 border-b-16 border-l-transparent border-r-transparent border-b-red-500"></div>
            </div>
          </div>

          {/* Spin indicator */}
          {isSpinning && (
            <div className="text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-full">
                <RotateCw className="w-4 h-4 animate-spin" />
                <span className="font-medium">
                  {language === 'ar' ? 'الدوران جاري...' : 'Spinning...'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Games List */}
      <div className={`rounded-xl border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="p-4 border-b border-slate-200">
          <div className="flex flex-col sm:flex-row gap-4">
            <input
              type="text"
              placeholder={language === 'ar' ? 'بحث عن لاعب...' : 'Search player...'}
              value={searchPlayer}
              onChange={(e) => setSearchPlayer(e.target.value)}
              className={`flex-1 px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
            />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as any)}
              className={`px-3 py-2 rounded-lg border ${isDark ? 'bg-slate-700 border-slate-600 text-white' : 'bg-white border-slate-200'}`}
            >
              <option value="all">{language === 'ar' ? 'الكل' : 'All'}</option>
              <option value="playing">{language === 'ar' ? 'يلعب' : 'Playing'}</option>
              <option value="won">{language === 'ar' ? 'فاز' : 'Won'}</option>
              <option value="lost">{language === 'ar' ? 'خسر' : 'Lost'}</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className={`border-b border-slate-200 ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
              <tr>
                <th className="text-right p-3 text-xs font-medium text-slate-600">
                  {language === 'ar' ? 'اللاعب' : 'Player'}
                </th>
                <th className="text-right p-3 text-xs font-medium text-slate-600">
                  {language === 'ar' ? 'الجائزة' : 'Prize'}
                </th>
                <th className="text-right p-3 text-xs font-medium text-slate-600">
                  {language === 'ar' ? 'القيمة' : 'Value'}
                </th>
                <th className="text-right p-3 text-xs font-medium text-slate-600">
                  {language === 'ar' ? 'الحالة' : 'Status'}
                </th>
                <th className="text-right p-3 text-xs font-medium text-slate-600">
                  {language === 'ar' ? 'الوقت' : 'Time'}
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center p-8">
                    <div className="inline-flex items-center gap-2">
                      <RotateCw className="w-4 h-4 animate-spin" />
                      <span className={isDark ? 'text-slate-400' : 'text-slate-600'}>
                        {language === 'ar' ? 'جاري التحميل...' : 'Loading...'}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : games.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center p-8">
                    <p className={isDark ? 'text-slate-400' : 'text-slate-600'}>
                      {language === 'ar' ? 'لا توجد ألعاب' : 'No games found'}
                    </p>
                  </td>
                </tr>
              ) : (
                games.map((game) => (
                  <tr key={game.id} className={`border-b border-slate-100 ${isDark ? 'hover:bg-slate-700/30' : 'hover:bg-slate-50'}`}>
                    <td className="p-3">
                      <div>
                        <p className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          {game.player_name}
                        </p>
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span>{game.prize_name}</span>
                      </div>
                    </td>
                    <td className="p-3">
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {fmt(game.prize_value)} {game.currency}
                      </p>
                    </td>
                    <td className="p-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium
                        ${game.status === 'won' ? 'bg-emerald-100 text-emerald-700' : 
                          game.status === 'lost' ? 'bg-red-100 text-red-700' : 
                          'bg-amber-100 text-amber-700'}
                      `}>
                        {game.status === 'won' ? (language === 'ar' ? 'فاز' : 'Won') :
                         game.status === 'lost' ? (language === 'ar' ? 'خسر' : 'Lost') :
                         (language === 'ar' ? 'يلعب' : 'Playing')}
                      </span>
                    </td>
                    <td className="p-3">
                      <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                        {new Date(game.created_at).toLocaleString(language === 'ar' ? 'ar-SA' : 'en-US')}
                      </p>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="p-4 border-t border-slate-200">
            <div className="flex items-center justify-between">
              <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                {language === 'ar' ? 'عرض' : 'Showing'} {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, total)} {language === 'ar' ? 'من' : 'of'} {total}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className={`px-3 py-1 rounded text-sm ${page === 1 ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'}`}
                >
                  {language === 'ar' ? 'السابق' : 'Previous'}
                </button>
                <button
                  onClick={() => setPage(p => Math.min(Math.ceil(total / PAGE_SIZE), p + 1))}
                  disabled={page >= Math.ceil(total / PAGE_SIZE)}
                  className={`px-3 py-1 rounded text-sm ${page >= Math.ceil(total / PAGE_SIZE) ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'}`}
                >
                  {language === 'ar' ? 'التالي' : 'Next'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Prize Modal */}
      {showPrizeModal && selectedPrize && (
        <Modal onClose={() => setShowPrizeModal(false)}>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center text-3xl"
                 style={{ backgroundColor: selectedPrize.color + '20' }}>
              {selectedPrize.icon}
            </div>
            <h3 className={`text-xl font-bold mb-2 ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {language === 'ar' ? 'مبارك!' : 'Congratulations!'}
            </h3>
            <p className={`text-lg mb-4 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
              {selectedPrize.name}
            </p>
            <p className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {fmt(selectedPrize.value)} {selectedPrize.currency}
            </p>
            <button
              onClick={() => setShowPrizeModal(false)}
              className="px-6 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
            >
              {language === 'ar' ? 'ممتاز' : 'Awesome!'}
            </button>
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

            {/* Top Prizes */}
            <div>
              <h4 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                {language === 'ar' ? 'أعلى الجوائز' : 'Top Prizes'}
              </h4>
              <div className="space-y-2">
                {stats.topPrizes.map((prize) => (
                  <div key={prize.id} className={`flex items-center justify-between p-3 rounded-lg ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                           style={{ backgroundColor: prize.color + '20' }}>
                        {prize.icon}
                      </div>
                      <span className={isDark ? 'text-white' : 'text-slate-900'}>{prize.name}</span>
                    </div>
                    <span className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      {fmt(prize.value)} {prize.currency}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Hourly Chart */}
            <div>
              <h4 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                {language === 'ar' ? 'إحصائيات 24 ساعة' : '24 Hour Stats'}
              </h4>
              <div className="h-48">
                <SparklineChart
                  data={stats.hourlyStats.map(s => s.games)}
                  color="#10b981"
                  height={192}
                />
              </div>
            </div>

            {/* Recent Games */}
            <div>
              <h4 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                {language === 'ar' ? 'الألعاب الأخيرة' : 'Recent Games'}
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {stats.recentGames.map((game) => (
                  <div key={game.id} className={`flex items-center justify-between p-2 rounded ${isDark ? 'bg-slate-700/30' : 'bg-slate-50'}`}>
                    <div>
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {game.player_name}
                      </p>
                      <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                        {game.prize_name}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {fmt(game.prize_value)} {game.currency}
                      </p>
                      <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                        {new Date(game.created_at).toLocaleTimeString(language === 'ar' ? 'ar-SA' : 'en-US')}
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
