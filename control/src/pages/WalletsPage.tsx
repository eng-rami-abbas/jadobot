import { useState, useEffect, useCallback } from 'react';
import { Wallet, Save, Trash2, Edit2, X, RefreshCw, AlertCircle, Lock, Smile } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { useRealtime } from '../hooks/useRealtime';

// 🔥 قائمة الإيموجيات الشائعة للمحافظ (60+ إيموجي)
const WALLET_EMOJIS = [
  // 💳 البطاقات والبنوك
  { emoji: '💳', name: 'بطاقة' },
  { emoji: '🏦', name: 'بنك' },
  { emoji: '🏧', name: 'ATM' },
  { emoji: '💰', name: 'أموال' },
  { emoji: '💵', name: 'دولار' },
  { emoji: '💶', name: 'يورو' },
  { emoji: '💷', name: 'جنيه' },
  { emoji: '💴', name: 'ين' },
  { emoji: '💸', name: 'تحويل' },
  { emoji: '🪙', name: 'عملة' },
  // 📱 رقمي
  { emoji: '📱', name: 'موبايل' },
  { emoji: '📲', name: 'محفظة' },
  { emoji: '💻', name: 'كمبيوتر' },
  { emoji: '🖥️', name: 'شاشة' },
  { emoji: '💾', name: 'ذاكرة' },
  { emoji: '💿', name: 'قرص' },
  // 💎 قيمة
  { emoji: '💎', name: 'الماس' },
  { emoji: '💍', name: 'خاتم' },
  { emoji: '�', name: 'تاج' },
  { emoji: '🏆', name: 'كأس' },
  { emoji: '🎁', name: 'هدية' },
  { emoji: '🎀', name: 'Ribbon' },
  // ⚡ سرعة وقوة
  { emoji: '⚡', name: 'سريع' },
  { emoji: '�', name: 'نار' },
  { emoji: '💥', name: 'قوة' },
  { emoji: '🚀', name: 'صاروخ' },
  { emoji: '✈️', name: 'طائرة' },
  { emoji: '🚁', name: 'طائرة2' },
  // �🔒 أمان
  { emoji: '🔒', name: 'آمن' },
  { emoji: '🔐', name: 'مغلق' },
  { emoji: '🔓', name: 'مفتوح' },
  { emoji: '🔑', name: 'مفتاح' },
  { emoji: '🗝️', name: 'مفتاح2' },
  { emoji: '🛡️', name: 'درع' },
  { emoji: '✅', name: 'موثوق' },
  { emoji: '☑️', name: 'صحيح' },
  // ⭐ تميز
  { emoji: '⭐', name: 'نجمة' },
  { emoji: '🌟', name: 'لمعان' },
  { emoji: '✨', name: 'ومض' },
  { emoji: '�', name: 'ألعاب' },
  { emoji: '🎇', name: 'ألعاب2' },
  { emoji: '🌠', name: 'شهاب' },
  // �🎯 أهداف
  { emoji: '🎯', name: 'هدف' },
  { emoji: '🎪', name: 'سيرك' },
  { emoji: '🎨', name: 'فن' },
  { emoji: '🎭', name: 'مسرح' },
  { emoji: '🎬', name: 'فيلم' },
  // 🌍 عالمي
  { emoji: '🌍', name: 'عالم' },
  { emoji: '🌎', name: 'أمريكا' },
  { emoji: '🌏', name: 'آسيا' },
  { emoji: '🌐', name: 'شبكة' },
  { emoji: '🗺️', name: 'خريطة' },
  // 🌈 ألوان
  { emoji: '🔵', name: 'أزرق' },
  { emoji: '🔴', name: 'أحمر' },
  { emoji: '🟢', name: 'أخضر' },
  { emoji: '🟡', name: 'أصفر' },
  { emoji: '🟣', name: 'بنفسجي' },
  { emoji: '⚫', name: 'أسود' },
  { emoji: '⚪', name: 'أبيض' },
  { emoji: '🟤', name: 'بني' },
  { emoji: '🟠', name: 'برتقالي' },
  // 🌊 طبيعة
  { emoji: '🌊', name: 'موج' },
  { emoji: '🔵', name: 'دائرة' },
  { emoji: '♦️', name: 'ماس' },
  { emoji: '♠️', name: 'سبع' },
  { emoji: '♥️', name: 'قلب' },
  { emoji: '♣️', name: 'صوب' },
];

type WalletType = {
  id: string;
  name: string;
  key: string;
  wallet_number: string;
  address: string;
  title: string;
  image_url: string;
  header_text: string;  // 🔥 النص الأول (قبل العنوان)
  message_template: string;  // 🔥 النص الثاني (بعد العنوان)
  is_active: boolean;
  sort_order: number;
  bonus_percentage?: number;
};

export default function WalletsPage() {
  const { theme, language, isAuthenticated } = useApp();
  const isDark = theme === 'dark';

  const [wallets, setWallets] = useState<WalletType[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saveLoading, setSaveLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);  // 🔥 عرض/إخفاء قائمة الإيموجي

  const [form, setForm] = useState({
    name: '',
    key: '',
    wallet_number: '',
    address: '',
    title: '',
    image_url: '',
    header_text: '',  // 🔥 النص الأول (قبل العنوان)
    message_template: '',  // 🔥 النص الثاني (بعد العنوان)
    is_active: true,
    sort_order: 0,
    bonus_percentage: 0
  });
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);  // 🔥 موقع المؤشر في حقل الاسم

  const loadWallets = useCallback(async () => {
    if (!isAuthenticated) {
      console.warn('User not authenticated - wallets will not load due to RLS policies');
      return;
    }

    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('wallets')
        .select('*')
        .order('sort_order');

      if (error) {
        console.error('Error loading wallets:', error);
        alert('خطأ في تحميل المحافظ: ' + error.message);
      } else {
        console.log('Loaded wallets:', data);
        setWallets(data || []);
      }
    } catch (e) {
      console.error('Exception loading wallets:', e);
    }
    setLoading(false);
  }, [isAuthenticated]);

  useEffect(() => {
    loadWallets();
  }, [loadWallets]);

  useRealtime({
    table: 'wallets',
    onInsert: () => {
      console.log('[WalletsPage] New wallet inserted, reloading...');
      loadWallets();
    },
    onUpdate: () => {
      console.log('[WalletsPage] Wallet updated, reloading...');
      loadWallets();
    },
    onDelete: () => {
      console.log('[WalletsPage] Wallet deleted, reloading...');
      loadWallets();
    }
  });

  const generateKey = (name: string) => {
    return name
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '_')
      .replace(/[^\w_]/g, '');
  };

  const saveWallet = async () => {
    if (!form.name || !form.wallet_number) {
      alert(language === 'ar' ? 'يرجى ملء الاسم ورقم المحفظة' : 'Please fill name and wallet number');
      return;
    }

    setSaveLoading(true);
    const key = generateKey(form.name);

    const payload = {
      name: form.name,
      key,
      wallet_number: form.wallet_number,
      address: form.address || form.wallet_number,
      title: form.title || form.name,
      image_url: form.image_url || '',
      header_text: form.header_text || '',  // 🔥 النص الأول
      message_template: form.message_template,  // 🔥 النص الثاني
      is_active: form.is_active,
      sort_order: form.sort_order,
      bonus_percentage: Number(form.bonus_percentage) || 0
    };

    try {
      console.log('Saving wallet with payload:', payload);
      console.log('Editing ID:', editingId);

      let result;
      if (editingId) {
        result = await supabase
          .from('wallets')
          .update(payload)
          .eq('id', editingId);
      } else {
        result = await supabase
          .from('wallets')
          .insert([payload])
          .select();
      }

      console.log('Supabase result:', result);

      if (result.error) {
        console.error('Save error:', result.error);
        const errorMsg = result.error.message || result.error.code || 'Unknown error';
        alert(language === 'ar' ? `خطأ في الحفظ: ${errorMsg}` : `Save error: ${errorMsg}`);
        return;
      }

      // Reset form
      setForm({
        name: '',
        key: '',
        wallet_number: '',
        address: '',
        title: '',
        image_url: '',
        header_text: '',  // 🔥 النص الأول
        message_template: '',  // 🔥 النص الثاني
        is_active: true,
        sort_order: 0,
        bonus_percentage: 0
      });
      setCursorPosition(null);

      setEditingId(null);
      await loadWallets();
    } catch (e) {
      console.error('Exception saving wallet:', e);
      alert(language === 'ar' ? 'حدث خطأ غير متوقع' : 'Unexpected error');
    } finally {
      setSaveLoading(false);
    }
  };

  const deleteWallet = async (id: string) => {
    if (!confirm(language === 'ar' ? 'هل أنت متأكد من حذف هذه المحفظة؟' : 'Are you sure you want to delete this wallet?')) {
      return;
    }

    setDeleteLoading(id);
    try {
      console.log('Deleting wallet ID:', id);
      const result = await supabase
        .from('wallets')
        .delete()
        .eq('id', id);

      console.log('Delete result:', result);

      if (result.error) {
        console.error('Delete error:', result.error);
        const errorMsg = result.error.message || result.error.code || 'Unknown error';
        alert(language === 'ar' ? `خطأ في الحذف: ${errorMsg}` : `Delete error: ${errorMsg}`);
        return;
      }

      alert(language === 'ar' ? '✅ تم الحذف بنجاح' : '✅ Deleted successfully');
      await loadWallets();
    } catch (e) {
      console.error('Exception deleting wallet:', e);
      alert(language === 'ar' ? `حدث خطأ غير متوقع: ${e}` : `Unexpected error: ${e}`);
    } finally {
      setDeleteLoading(null);
    }
  };

  const startEdit = (w: WalletType) => {
    setEditingId(w.id);
    setForm({
      name: w.name,
      key: w.key,
      wallet_number: w.wallet_number,
      address: w.address,
      title: w.title,
      image_url: w.image_url,
      header_text: w.header_text || '',  // 🔥 النص الأول
      message_template: w.message_template,  // 🔥 النص الثاني
      is_active: w.is_active,
      sort_order: w.sort_order,
      bonus_percentage: w.bonus_percentage || 0
    });
  };

  const card = `rounded-2xl border p-4 space-y-3 ${
    isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
  }`;

  const input = `w-full px-3 py-2 rounded-xl text-sm border outline-none ${
    isDark
      ? 'bg-slate-900 border-slate-700 text-white'
      : 'bg-slate-50 border-slate-200 text-slate-800'
  }`;

  return (
    <div className="space-y-4">
      {/* HEADER */}
      <div className={card}>
        <div className="flex items-center gap-2 mb-3">
          <Wallet size={18} />
          <h2 className="font-semibold">
            {language === 'ar' ? 'إدارة المحافظ' : 'Wallet Management'}
          </h2>
        </div>

        {/* FORM */}
        <div className="grid md:grid-cols-2 gap-4">

          {/* 🔥 حقل الاسم مع زر اختيار الإيموجي */}
          <div className="space-y-1 md:col-span-2">
            <label className="text-xs font-medium opacity-70">
              {language === 'ar' ? 'اسم المحفظة *' : 'Wallet Name *'}
            </label>
            <div className="flex gap-2">
              {/* زر اختيار الإيموجي */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                  className={`
                    h-full px-3 rounded-xl text-xl border outline-none transition-all flex items-center justify-center
                    ${isDark 
                      ? 'bg-slate-900 border-slate-700 hover:bg-slate-800 text-yellow-400' 
                      : 'bg-white border-slate-200 hover:bg-slate-50 text-yellow-500'
                    }
                  `}
                  title={language === 'ar' ? 'اختر الإيموجي (يدرج في الاسم)' : 'Choose emoji (inserts in name)'}
                >
                  <Smile size={22} />
                </button>

                {/* 🔥 قائمة الإيموجيات المنبثقة */}
                {showEmojiPicker && (
                  <div 
                    className={`
                      absolute z-50 top-full mt-2 left-0 w-72 p-3 rounded-xl border shadow-xl
                      ${isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}
                    `}
                  >
                    <div className="grid grid-cols-8 gap-1 max-h-64 overflow-y-auto">
                      {WALLET_EMOJIS.map(({ emoji, name }) => (
                        <button
                          key={emoji}
                          type="button"
                          onClick={() => {
                            // 🔥 إدراج الإيموجي في نص الاسم عند موقع المؤشر
                            const currentName = form.name;
                            const pos = cursorPosition !== null ? cursorPosition : currentName.length;
                            const newName = currentName.slice(0, pos) + emoji + currentName.slice(pos);
                            setForm({ ...form, name: newName });
                            setShowEmojiPicker(false);
                          }}
                          className={`
                            flex items-center justify-center p-2 rounded-lg text-xl transition-all
                            ${isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}
                          `}
                          title={name}
                        >
                          {emoji}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* حقل الاسم */}
              <input
                className={`${input} flex-1`}
                placeholder={language === 'ar' ? 'مثال: بنك Bemo 💳' : 'e.g. Bemo Bank 💳'}
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                onSelect={e => setCursorPosition(e.currentTarget.selectionStart || 0)}
                onClick={e => setCursorPosition(e.currentTarget.selectionStart || 0)}
                onKeyUp={e => setCursorPosition(e.currentTarget.selectionStart || 0)}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium opacity-70">
              {language === 'ar' ? 'رقم المحفظة *' : 'Wallet Number *'}
            </label>
            <input
              className={input}
              placeholder={language === 'ar' ? 'رقم الحساب للتحويل' : 'Account number for transfers'}
              value={form.wallet_number}
              onChange={e => setForm({ ...form, wallet_number: e.target.value })}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium opacity-70">
              {language === 'ar' ? 'رابط صورة المحفظة (اختياري)' : 'Wallet Image URL (optional)'}
            </label>
            <input
              className={input}
              placeholder="https://..."
              value={form.image_url}
              onChange={e => setForm({ ...form, image_url: e.target.value })}
            />
          </div>

          {/* 🔥 النص الأول - قبل العنوان */}
          <div className="space-y-1 md:col-span-2">
            <label className="text-xs font-medium opacity-70">
              {language === 'ar' ? 'النص الأول (قبل العنوان)' : 'First Text (before title)'}
            </label>
            <input
              className={input}
              placeholder={language === 'ar' ? 'مثال: 💳 طريقة الدفع المختارة:' : 'e.g. 💳 Selected payment method:'}
              value={form.header_text}
              onChange={e => setForm({ ...form, header_text: e.target.value })}
            />
          </div>

          {/* 🔥 النص الثاني - بعد العنوان */}
          <div className="space-y-1 md:col-span-2">
            <label className="text-xs font-medium opacity-70">
              {language === 'ar' ? 'النص الثاني (بعد العنوان)' : 'Second Text (after title)'}
            </label>
            <input
              className={input}
              placeholder={language === 'ar' ? 'مثال: يرجى التحويل إلى هذا الرقم ثم إدخال رقم العملية' : 'e.g. Please transfer to this number then enter operation number'}
              value={form.message_template}
              onChange={e => setForm({ ...form, message_template: e.target.value })}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium opacity-70">
              {language === 'ar' ? 'الترتيب (0 = الأولى)' : 'Sort Order (0 = first)'}
            </label>
            <input
              type="number"
              className={input}
              placeholder="0"
              value={form.sort_order}
              onChange={e => setForm({ ...form, sort_order: Number(e.target.value) })}
            />
            <p className="text-[10px] opacity-50">
              {language === 'ar' ? 'ترتيب ظهور المحفظة في القائمة' : 'Order of appearance in list'}
            </p>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium opacity-70">
              {language === 'ar' ? 'نسبة البونص % (0 = لا بونص)' : 'Bonus % (0 = no bonus)'}
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              className={input}
              placeholder="0"
              value={form.bonus_percentage}
              onChange={e => setForm({ ...form, bonus_percentage: Number(e.target.value) })}
            />
            <p className="text-[10px] opacity-50">
              {language === 'ar' ? 'نسبة إضافية على المبلغ عند الموافقة على الإيداع' : 'Extra percentage added to amount when deposit is approved'}
            </p>
          </div>

          <div className="flex items-center gap-2 md:col-span-2">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={e => setForm({ ...form, is_active: e.target.checked })}
              className="w-4 h-4"
            />
            <label htmlFor="is_active" className="text-sm">
              {language === 'ar' ? 'المحفظة نشطة (متاحة للاستخدام)' : 'Wallet is active (available for use)'}
            </label>
          </div>
        </div>

        {/* DEBUG INFO */}
        {!isAuthenticated && (
          <div className="mt-2 p-2 rounded-lg bg-red-500/20 text-red-400 text-xs">
            ⚠️ {language === 'ar' ? 'أنت غير مسجل الدخول - لن يعمل الحفظ' : 'Not logged in - save will not work'}
          </div>
        )}

        {/* BUTTONS */}
        <div className="flex gap-2 mt-3">
          <button
            onClick={async () => {
              const { data: { session } } = await supabase.auth.getSession();
              console.log('Auth session:', session);
              alert(session
                ? (language === 'ar' ? `✅ مسجل دخول: ${session.user.email}` : `✅ Logged in: ${session.user.email}`)
                : (language === 'ar' ? '❌ غير مسجل دخول' : '❌ Not logged in')
              );
            }}
            className="px-3 py-2 bg-slate-600 text-white rounded-xl text-xs"
          >
            🔍 {language === 'ar' ? 'فحص Auth' : 'Check Auth'}
          </button>

          <button
            onClick={saveWallet}
            disabled={saveLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl disabled:opacity-50"
          >
            <Save size={14} className={saveLoading ? 'animate-spin' : ''} />
            {editingId
              ? (language === 'ar' ? 'تحديث' : 'Update')
              : (language === 'ar' ? 'إضافة' : 'Add')}
          </button>

          {editingId && (
            <button
              onClick={() => {
                setEditingId(null);
                setForm({
                  name: '',
                  key: '',
                  wallet_number: '',
                  address: '',
                  title: '',
                  image_url: '',
                  header_text: '',  // 🔥 النص الأول
                  message_template: '',  // 🔥 النص الثاني
                  is_active: true,
                  sort_order: 0,
                  bonus_percentage: 0
                });
                setCursorPosition(null);
              }}
              className="px-4 py-2 rounded-xl border"
              disabled={saveLoading}
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* WALLETS LIST SECTION */}
      <div className={card}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">
            {language === 'ar' ? 'قائمة المحافظ' : 'Wallets List'}
            <span className="ml-2 text-sm opacity-60">({wallets.length})</span>
          </h3>
          <button
            onClick={loadWallets}
            disabled={loading}
            className="p-2 rounded-lg hover:bg-slate-200/20 transition-colors disabled:opacity-50"
            title={language === 'ar' ? 'تحديث' : 'Refresh'}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        {!isAuthenticated ? (
          <div className="text-center py-8 text-amber-400">
            <Lock size={32} className="mx-auto mb-2 opacity-60" />
            <p className="text-sm opacity-80 mb-2">
              {language === 'ar'
                ? 'يجب تسجيل الدخول لعرض المحافظ'
                : 'Login required to view wallets'}
            </p>
            <p className="text-xs opacity-60">
              (RLS policies block anonymous access)
            </p>
          </div>
        ) : loading ? (
          <div className="text-center py-8">
            <RefreshCw size={24} className="animate-spin mx-auto mb-2 opacity-60" />
            <p className="text-sm opacity-60">
              {language === 'ar' ? 'جاري التحميل...' : 'Loading...'}
            </p>
          </div>
        ) : wallets.length === 0 ? (
          <div className="text-center py-8">
            <AlertCircle size={32} className="mx-auto mb-2 opacity-40" />
            <p className="text-sm opacity-60 mb-2">
              {language === 'ar' ? 'لا توجد محافظ - أضف محفظة جديدة' : 'No wallets - Add a new wallet'}
            </p>
            <p className="text-xs opacity-40">
              {language === 'ar'
                ? 'إذا كنت متأكداً من وجود محافظ في Supabase، تحقق من Row Level Security'
                : 'If wallets exist in Supabase, check Row Level Security policies'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {wallets.map(w => (
              <div
                key={w.id}
                className={`rounded-xl border p-4 ${
                  isDark
                    ? 'bg-slate-900/50 border-slate-700'
                    : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex gap-4">
                  {/* صورة المحفظة */}
                  {w.image_url && (
                    <div className="shrink-0">
                      <img
                        src={w.image_url}
                        alt={w.name}
                        className="w-24 h-24 object-cover rounded-lg border"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                    </div>
                  )}

                  {/* بيانات المحفظة */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold text-lg">{w.name}</p>
                        <p className="text-sm opacity-70 font-mono">{w.wallet_number}</p>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button
                          onClick={() => startEdit(w)}
                          className="p-2 rounded-lg hover:bg-slate-200/20 transition-colors"
                          title={language === 'ar' ? 'تعديل' : 'Edit'}
                          disabled={deleteLoading === w.id}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => deleteWallet(w.id)}
                          className="p-2 rounded-lg hover:bg-red-500/20 text-red-400 transition-colors"
                          title={language === 'ar' ? 'حذف' : 'Delete'}
                          disabled={deleteLoading === w.id}
                        >
                          {deleteLoading === w.id ? (
                            <RefreshCw size={16} className="animate-spin" />
                          ) : (
                            <Trash2 size={16} />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* رسالة البوت */}
                    {w.message_template && (
                      <p className="text-sm opacity-60 mt-2 italic">
                        "{w.message_template}"
                      </p>
                    )}

                    {/* الإيموجي والمعلومات */}
                    <div className="flex items-center gap-2 mt-2">
                      {/* 🔥 استخراج الإيموجي الأول من الاسم أو استخدام افتراضي */}
                      <span className="text-2xl">
                        {w.name.match(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1F018}-\u{1F270}\u{238C}\u{2B06}\u{2B07}\u{2B05}\u{27A1}\u{2194}-\u{2199}\u{21A9}\u{21AA}\u{2934}\u{2935}\u{25AA}\u{25AB}\u{25FE}\u{25FD}\u{25FB}\u{25B6}\u{25C0}\u{1F200}-\u{1F251}]/u)?.[0] || '💳'}
                      </span>
                    </div>

                    {/* معلومات إضافية */}
                    <div className="flex flex-wrap gap-2 mt-3">
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-300 font-mono">
                        {w.key}
                      </span>
                      {w.is_active ? (
                        <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-300">
                          {language === 'ar' ? 'نشط' : 'Active'}
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-1 rounded-full bg-red-500/20 text-red-300">
                          {language === 'ar' ? 'معطل' : 'Inactive'}
                        </span>
                      )}
                      <span className="text-xs px-2 py-1 rounded-full bg-slate-500/20 opacity-70">
                        #{w.sort_order}
                      </span>
                      {(w.bonus_percentage || 0) > 0 && (
                        <span className="text-xs px-2 py-1 rounded-full bg-amber-500/20 text-amber-300">
                          🎁 {w.bonus_percentage}% {language === 'ar' ? 'بونص' : 'Bonus'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
