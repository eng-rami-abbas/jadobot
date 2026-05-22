import { useState, useEffect, useCallback } from 'react';
import { CreditCard, Save, Trash2, Edit2, X, RefreshCw, AlertCircle, Percent, MessageSquare } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import type { WithdrawalMethod } from '../types';

export default function WithdrawalMethodsPage() {
  const { theme, isAuthenticated } = useApp();
  const isDark = theme === 'dark';

  const [methods, setMethods] = useState<WithdrawalMethod[]>([]);
  const [loading, setLoading] = useState(false);
  const [globalFee, setGlobalFee] = useState(5.0);
  const [approvedMsg, setApprovedMsg] = useState('');
  const [rejectedMsg, setRejectedMsg] = useState('');

  const [editingId, setEditingId] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: '',
    key: '',
    fee_percentage: 5.0,
    input_label: 'أدخل رقم الحساب',
    is_active: true,
    sort_order: 0
  });

  // ================= LOAD =================
  const loadMethods = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('withdrawal_methods')
        .select('*')
        .order('sort_order');

      if (error) {
        console.error('Error loading methods:', error);
        alert('خطأ في تحميل طرق السحب: ' + error.message);
      } else {
        setMethods(data || []);
      }

      // Load global settings
      const { data: settings } = await supabase
        .from('app_settings')
        .select('key, value')
        .in('key', ['withdrawal_fee_percentage', 'withdrawal_approved_message', 'withdrawal_rejected_message']);

      if (settings) {
        settings.forEach(s => {
          if (s.key === 'withdrawal_fee_percentage') setGlobalFee(parseFloat(s.value) || 5.0);
          if (s.key === 'withdrawal_approved_message') setApprovedMsg(s.value || '');
          if (s.key === 'withdrawal_rejected_message') setRejectedMsg(s.value || '');
        });
      }
    } catch (e) {
      console.error('Exception:', e);
    }
    setLoading(false);
  }, [isAuthenticated]);

  useEffect(() => {
    loadMethods();
  }, [loadMethods]);

  // ================= KEY NORMALIZER =================
  const generateKey = (name: string) => {
    return name
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '_')
      .replace(/[^\w_]/g, '');
  };

  // ================= SAVE SETTINGS =================
  const saveSettings = async () => {
    try {
      const settings = [
        { key: 'withdrawal_fee_percentage', value: globalFee.toString() },
        { key: 'withdrawal_approved_message', value: approvedMsg },
        { key: 'withdrawal_rejected_message', value: rejectedMsg }
      ];

      for (const s of settings) {
        await supabase.from('app_settings').upsert({ key: s.key, value: s.value });
      }

      alert('✅ تم حفظ الإعدادات');
    } catch (e) {
      alert('❌ خطأ في الحفظ');
    }
  };

  // ================= SAVE METHOD =================
  const saveMethod = async () => {
    const key = editingId || generateKey(form.name);

    const payload = {
      name: form.name,
      key,
      fee_percentage: form.fee_percentage,
      input_label: form.input_label,
      is_active: form.is_active,
      sort_order: form.sort_order
    };

    try {
      if (editingId) {
        const { error } = await supabase
          .from('withdrawal_methods')
          .update(payload)
          .eq('id', editingId);
        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('withdrawal_methods')
          .insert(payload);
        if (error) throw error;
      }

      await loadMethods();
      setEditingId(null);
      resetForm();
      alert('✅ تم حفظ طريقة السحب');
    } catch (error: any) {
      alert('❌ خطأ في الحفظ: ' + error.message);
    }
  };

  // ================= DELETE =================
  const deleteMethod = async (id: string) => {
    if (!confirm('هل أنت متأكد من الحذف؟')) return;

    try {
      const { error } = await supabase
        .from('withdrawal_methods')
        .delete()
        .eq('id', id);

      if (error) throw error;
      await loadMethods();
      alert('✅ تم الحذف');
    } catch (error: any) {
      alert('❌ خطأ في الحذف: ' + error.message);
    }
  };

  // ================= EDIT =================
  const startEdit = (method: WithdrawalMethod) => {
    setEditingId(method.id);
    setForm({
      name: method.name,
      key: method.key,
      fee_percentage: method.fee_percentage,
      input_label: method.input_label,
      is_active: method.is_active,
      sort_order: method.sort_order || 0
    });
  };

  // ================= RESET =================
  const resetForm = () => {
    setEditingId(null);
    setForm({
      name: '',
      key: '',
      fee_percentage: 5.0,
      input_label: 'أدخل رقم الحساب',
      is_active: true,
      sort_order: 0
    });
  };

  // ================= TOGGLE ACTIVE =================
  const toggleActive = async (method: WithdrawalMethod) => {
    try {
      const { error } = await supabase
        .from('withdrawal_methods')
        .update({ is_active: !method.is_active })
        .eq('id', method.id);

      if (error) throw error;
      await loadMethods();
    } catch (error: any) {
      alert('❌ خطأ: ' + error.message);
    }
  };

  return (
    <div className={`p-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <CreditCard className="w-6 h-6 text-blue-500" />
          طرق السحب
        </h1>
        <button
          onClick={loadMethods}
          className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white"
          disabled={loading}
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Global Settings */}
      <div className={`p-4 rounded-lg mb-6 ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Percent className="w-5 h-5 text-green-500" />
          الإعدادات العامة
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">نسبة الخصم الافتراضية (%)</label>
            <input
              type="number"
              step="0.01"
              value={globalFee}
              onChange={(e) => setGlobalFee(parseFloat(e.target.value))}
              className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`}
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            رسالة الموافقة
          </label>
          <textarea
            value={approvedMsg}
            onChange={(e) => setApprovedMsg(e.target.value)}
            rows={3}
            className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`}
            placeholder="{amount_syp} {fee_percentage} {net_amount} {method_name} {operation_number}"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            رسالة الرفض
          </label>
          <textarea
            value={rejectedMsg}
            onChange={(e) => setRejectedMsg(e.target.value)}
            rows={2}
            className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`}
          />
        </div>

        <button
          onClick={saveSettings}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2"
        >
          <Save className="w-4 h-4" />
          حفظ الإعدادات
        </button>
      </div>

      {/* Form */}
      <div className={`p-4 rounded-lg mb-6 ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <h2 className="text-lg font-semibold mb-4">
          {editingId ? 'تعديل طريقة سحب' : 'إضافة طريقة سحب'}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">الاسم *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300'}`}
              placeholder="Syriatel Cash"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">المفتاح</label>
            <input
              type="text"
              value={editingId ? form.key : generateKey(form.name)}
              readOnly
              className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-gray-400' : 'bg-gray-100 border-gray-300 text-gray-500'}`}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">ترتيب الزر في البوت</label>
            <input
              type="number"
              value={form.sort_order}
              onChange={(e) => setForm({ ...form, sort_order: parseInt(e.target.value) || 0 })}
              className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300'}`}
              placeholder="0"
              min="0"
            />
            <p className="text-xs text-gray-500 mt-1">0 = الأول، 1 = الثاني، ...</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">نسبة الخصم (%)</label>
            <input
              type="number"
              step="0.01"
              value={form.fee_percentage}
              onChange={(e) => setForm({ ...form, fee_percentage: parseFloat(e.target.value) })}
              className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300'}`}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">نص طلب العنوان</label>
            <input
              type="text"
              value={form.input_label}
              onChange={(e) => setForm({ ...form, input_label: e.target.value })}
              className={`w-full p-2 rounded-lg border ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-300'}`}
              placeholder="أدخل رقم الحساب"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="w-5 h-5"
              />
              <span className="text-sm font-medium">نشط</span>
            </label>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={saveMethod}
            disabled={!form.name}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {editingId ? 'تحديث' : 'إضافة'}
          </button>
          {editingId && (
            <button
              onClick={resetForm}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              إلغاء
            </button>
          )}
        </div>
      </div>

      {/* List */}
      <div className="grid grid-cols-1 gap-3">
        {methods.map((method) => (
          <div
            key={method.id}
            className={`p-4 rounded-lg border ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} ${!method.is_active ? 'opacity-60' : ''}`}
          >
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-3">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${isDark ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-600'}`}>
                  {method.sort_order || 0}
                </span>
                <div>
                  <h3 className="font-semibold">{method.name}</h3>
                  <p className="text-sm text-gray-500">
                    نسبة الخصم: {method.fee_percentage}% | {method.input_label}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleActive(method)}
                  className={`p-2 rounded ${method.is_active ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}
                  title={method.is_active ? 'تعطيل' : 'تفعيل'}
                >
                  {method.is_active ? '🟢' : '🔴'}
                </button>
                <button
                  onClick={() => startEdit(method)}
                  className="p-2 rounded bg-blue-100 text-blue-600 hover:bg-blue-200"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deleteMethod(method.id)}
                  className="p-2 rounded bg-red-100 text-red-600 hover:bg-red-200"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}

        {methods.length === 0 && (
          <div className={`p-8 text-center rounded-lg ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-500">لا توجد طرق سحب</p>
          </div>
        )}
      </div>
    </div>
  );
}
