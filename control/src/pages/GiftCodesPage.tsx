import { useState, useEffect, useCallback } from 'react';
import { Gift, Trash2, Edit2, X, Save, RefreshCw, Copy, CheckCircle } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { useRealtime } from '../hooks/useRealtime';

type GiftCode = {
  id: string;
  code: string;
  amount: number;
  is_used: boolean;
  used_by?: number;
  used_at?: string;
  created_at: string;
  notes?: string;
  expires_at?: string; // ⏰ تاريخ انتهاء الصلاحية
};

export default function GiftCodesPage() {
  const { theme, language, isAuthenticated } = useApp();
  const isDark = theme === 'dark';

  const [codes, setCodes] = useState<GiftCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const [form, setForm] = useState({
    code: '',
    amount: '',
    notes: '',
    expires_hours: '24' // ⏰ مدة الصلاحية بالساعات
  });
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // ================= LOAD =================
  const loadCodes = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      // 🔥 force refresh - تجاوز الكاش
      const { data, error } = await supabase
        .from('gift_codes')
        .select('*')
        .order('created_at', { ascending: false })
        .abortSignal(new AbortController().signal); // force fresh

      if (error) {
        console.error('Error loading gift codes:', error);
      } else {
        console.log('[GiftCodes] Loaded:', data);
        setCodes(data || []);
        setLastUpdated(new Date());
      }
    } catch (e) {
      console.error('Exception:', e);
    }
    setLoading(false);
  }, [isAuthenticated]);

  useEffect(() => {
    loadCodes();
  }, [loadCodes]);

  // Realtime updates
  useRealtime({
    table: 'gift_codes',
    onInsert: () => {
      console.log('[GiftCodes] New code inserted');
      loadCodes();
    },
    onUpdate: () => {
      console.log('[GiftCodes] Code updated');
      loadCodes();
    },
    onDelete: () => {
      console.log('[GiftCodes] Code deleted');
      loadCodes();
    }
  });

  // ================= GENERATE CODE =================
  const generateRandomCode = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 8; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return code;
  };

  // ================= SAVE =================
  const saveCode = async () => {
    if (!form.code || !form.amount) {
      alert(language === 'ar' ? 'يرجى ملء جميع الحقول' : 'Please fill all fields');
      return;
    }

    const code = form.code.toUpperCase().trim();
    const amount = Number(form.amount);

    if (amount <= 0) {
      alert(language === 'ar' ? 'المبلغ يجب أن يكون أكبر من 0' : 'Amount must be greater than 0');
      return;
    }

    // ⏰ حساب تاريخ الانتهاء
    const expiresHours = parseInt(form.expires_hours) || 24;
    const expiresAt = expiresHours > 0
      ? new Date(Date.now() + expiresHours * 60 * 60 * 1000).toISOString()
      : null; // null = لا نهائي

    const payload = {
      code,
      amount,
      notes: form.notes,
      expires_at: expiresAt
    };

    let query;
    if (editingCode) {
      query = supabase.from('gift_codes').update(payload).eq('code', editingCode);
    } else {
      query = supabase.from('gift_codes').insert([payload]);
    }

    const { error } = await query;

    if (error) {
      if (error.message.includes('duplicate')) {
        alert(language === 'ar' ? 'هذا الكود موجود مسبقاً' : 'This code already exists');
      } else {
        alert(error.message);
      }
      return;
    }

    setForm({ code: '', amount: '', notes: '', expires_hours: '24' });
    setEditingCode(null);
    loadCodes();
  };

  // ================= DELETE =================
  const deleteCode = async (codeObj: GiftCode) => {
    if (!confirm(language === 'ar' ? 'حذف الكود؟' : 'Delete code?')) return;

    console.log('[GiftCodes] Deleting code:', codeObj.code);
    // 🔥 استخدام code للحذف (id قد لا يكون موجوداً في الجدول)
    const { error } = await supabase.from('gift_codes').delete().eq('code', codeObj.code);

    if (error) {
      console.error('[GiftCodes] Delete error:', error);
      alert(language === 'ar' ? 'فشل الحذف: ' + error.message : 'Delete failed: ' + error.message);
    } else {
      console.log('[GiftCodes] Deleted successfully');
      loadCodes();
    }
  };

  // ================= EDIT =================
  const [editingCode, setEditingCode] = useState<string | null>(null); // 🔥 تخزين الكود بدلاً من id

  const startEdit = (code: GiftCode) => {
    setEditingCode(code.code); // استخدام الكود كمعرف
    setForm({
      code: code.code,
      amount: String(code.amount),
      notes: code.notes || '',
      expires_hours: '24' // default value
    });
  };

  // ================= COPY =================
  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  // ================= UI =================
  const card = `rounded-2xl border p-4 space-y-3 ${
    isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
  }`;

  const input = `w-full px-3 py-2 rounded-xl text-sm border outline-none ${
    isDark
      ? 'bg-slate-900 border-slate-700 text-white'
      : 'bg-slate-50 border-slate-200 text-slate-800'
  }`;

  const unusedCount = codes.filter(c => !c.is_used).length;
  const usedCount = codes.filter(c => c.is_used).length;
  const totalAmount = codes.reduce((sum, c) => sum + (c.is_used ? c.amount : 0), 0);

  return (
    <div className="space-y-4">
      {/* HEADER */}
      <div className={card}>
        <div className="flex items-center gap-2 mb-3">
          <Gift size={18} />
          <h2 className="font-semibold">
            {language === 'ar' ? 'إدارة أكواد الهدايا' : 'Gift Codes Management'}
          </h2>
        </div>

        {/* STATS */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className={`p-3 rounded-xl text-center ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`}>
            <div className="text-2xl font-bold text-green-500">{unusedCount}</div>
            <div className="text-xs opacity-70">{language === 'ar' ? 'غير مستخدم' : 'Unused'}</div>
          </div>
          <div className={`p-3 rounded-xl text-center ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`}>
            <div className="text-2xl font-bold text-blue-500">{usedCount}</div>
            <div className="text-xs opacity-70">{language === 'ar' ? 'مستخدم' : 'Used'}</div>
          </div>
          <div className={`p-3 rounded-xl text-center ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`}>
            <div className="text-2xl font-bold text-purple-500">{totalAmount.toLocaleString()}</div>
            <div className="text-xs opacity-70">{language === 'ar' ? 'تم توزيعه' : 'Distributed'}</div>
          </div>
        </div>

        {/* FORM */}
        <div className="grid md:grid-cols-3 gap-3">
          <div className="relative">
            <input
              className={input}
              placeholder={language === 'ar' ? 'الكود (مثال: ABC12345)' : 'Code (e.g. ABC12345)'}
              value={form.code}
              onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })}
              disabled={!!editingCode}
            />
            {!editingCode && (
              <button
                onClick={() => setForm({ ...form, code: generateRandomCode() })}
                className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-blue-500 hover:text-blue-600"
              >
                {language === 'ar' ? 'توليد' : 'Generate'}
              </button>
            )}
          </div>

          <input
            className={input}
            type="number"
            placeholder={language === 'ar' ? 'المبلغ (ل.س)' : 'Amount (SYP)'}
            value={form.amount}
            onChange={e => setForm({ ...form, amount: e.target.value })}
          />

          <input
            className={input}
            placeholder={language === 'ar' ? 'ملاحظات (اختياري)' : 'Notes (optional)'}
            value={form.notes}
            onChange={e => setForm({ ...form, notes: e.target.value })}
          />

          {/* ⏰ مدة صلاحية الكود */}
          <select
            className={input}
            value={form.expires_hours}
            onChange={e => setForm({ ...form, expires_hours: e.target.value })}
            disabled={!!editingCode}
          >
            <option value="24">{language === 'ar' ? '⏰ 24 ساعة' : '⏰ 24 hours'}</option>
            <option value="48">{language === 'ar' ? '⏰ 48 ساعة' : '⏰ 48 hours'}</option>
            <option value="72">{language === 'ar' ? '⏰ 72 ساعة' : '⏰ 72 hours'}</option>
            <option value="168">{language === 'ar' ? '⏰ 7 أيام' : '⏰ 7 days'}</option>
            <option value="0">{language === 'ar' ? '♾️ لا نهائي' : '♾️ No expiry'}</option>
          </select>
        </div>

        {/* BUTTONS */}
        <div className="flex gap-2 mt-3">
          <button
            onClick={saveCode}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700"
          >
            <Save size={14} />
            {editingCode
              ? (language === 'ar' ? 'حفظ التغييرات' : 'Save Changes')
              : (language === 'ar' ? 'إضافة' : 'Add')}
          </button>

          {editingCode && (
            <button
              onClick={() => {
                setEditingCode(null);
                setForm({ code: '', amount: '', notes: '', expires_hours: '24' });
              }}
              className="px-4 py-2 rounded-xl border hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* CODES LIST */}
      <div className={card}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold">
              {language === 'ar' ? 'قائمة الأكواد' : 'Codes List'}
              <span className="ml-2 text-sm opacity-60">({codes.length})</span>
            </h3>
            {lastUpdated && (
              <p className="text-xs opacity-50 mt-1">
                {language === 'ar' ? 'آخر تحديث: ' : 'Last updated: '}
                {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          <button
            onClick={loadCodes}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            {language === 'ar' ? 'تحديث' : 'Refresh'}
          </button>
        </div>

        {/* TABLE - Grid Layout for better alignment */}
        <div className="overflow-x-auto">
          <div className="min-w-[800px]">
            {/* HEADER */}
            <div className={`grid grid-cols-7 gap-4 p-3 text-sm font-medium border-b ${isDark ? 'border-slate-700 bg-slate-800/50' : 'border-slate-200 bg-slate-50'}`}>
              <div className="text-left">{language === 'ar' ? 'الكود' : 'Code'}</div>
              <div className="text-left">{language === 'ar' ? 'المبلغ' : 'Amount'}</div>
              <div className="text-left">{language === 'ar' ? 'الحالة' : 'Status'}</div>
              <div className="text-left">{language === 'ar' ? 'مستخدم من' : 'Used By'}</div>
              <div className="text-left">{language === 'ar' ? 'تاريخ الاستخدام' : 'Used At'}</div>
              <div className="text-left">{language === 'ar' ? 'ينتهي في' : 'Expires'}</div>
              <div className="text-left">{language === 'ar' ? 'الإجراءات' : 'Actions'}</div>
            </div>

            {/* ROWS */}
            <div className={`divide-y ${isDark ? 'divide-slate-700' : 'divide-slate-200'}`}>
              {codes.map(code => (
                <div key={code.id} className={`grid grid-cols-7 gap-4 p-3 items-center hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors`}>
                  {/* CODE */}
                  <div className="flex items-center gap-2">
                    <code className={`px-2 py-1 rounded text-sm font-mono ${
                      code.is_used
                        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                        : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    }`}>
                      {code.code}
                    </code>
                    <button
                      onClick={() => copyCode(code.code)}
                      className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 flex-shrink-0"
                      title="Copy"
                    >
                      {copiedCode === code.code ? (
                        <CheckCircle size={14} className="text-green-500" />
                      ) : (
                        <Copy size={14} />
                      )}
                    </button>
                  </div>

                  {/* AMOUNT */}
                  <div className="text-sm">{code.amount.toLocaleString()} {language === 'ar' ? 'ل.س' : 'SYP'}</div>

                  {/* STATUS */}
                  <div>
                    {code.is_used ? (
                      <span className="inline-block px-2 py-1 rounded-full text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                        ❌ {language === 'ar' ? 'مستخدم' : 'Used'}
                      </span>
                    ) : (
                      <span className="inline-block px-2 py-1 rounded-full text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        ✅ {language === 'ar' ? 'متاح' : 'Available'}
                      </span>
                    )}
                  </div>

                  {/* USED BY */}
                  <div className="text-sm font-mono">{code.used_by || '-'}</div>

                  {/* USED AT */}
                  <div className="text-sm">
                    {code.used_at
                      ? new Date(code.used_at).toLocaleDateString(language === 'ar' ? 'ar-SY' : 'en-US')
                      : '-'}
                  </div>

                  {/* EXPIRES AT */}
                  <div className="text-sm">
                    {code.expires_at ? (
                      new Date(code.expires_at) < new Date() ? (
                        <span className="text-red-500">⏰ {language === 'ar' ? 'منتهي' : 'Expired'}</span>
                      ) : (
                        new Date(code.expires_at).toLocaleDateString(language === 'ar' ? 'ar-SY' : 'en-US')
                      )
                    ) : (
                      '-'
                    )}
                  </div>

                  {/* ACTIONS */}
                  <div className="flex gap-1">
                    {!code.is_used && !editingCode && (
                      <button
                        onClick={() => startEdit(code)}
                        className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-700"
                        title="Edit"
                      >
                        <Edit2 size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => deleteCode(code)}
                      className="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500"
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {codes.length === 0 && (
          <div className="text-center py-8 opacity-50">
            {language === 'ar' ? 'لا توجد أكواد هدايا' : 'No gift codes found'}
          </div>
        )}
      </div>
    </div>
  );
}
