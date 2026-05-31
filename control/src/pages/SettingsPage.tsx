import { useState, useEffect, useCallback } from 'react';
import {
  Globe,
  Palette,
  DollarSign,
  Shield,
  Save,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  Pause,
  Play
} from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';

type SettingsTab = 'general' | 'security' | 'bot';

export default function SettingsPage() {
  const { theme, setTheme, language, setLanguage, exchangeRate, refreshExchangeRate } = useApp();
  const isDark = theme === 'dark';
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [botStatus, setBotStatus] = useState<'active' | 'paused'>('active');
  const [botStatusMsg, setBotStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [rateInput, setRateInput] = useState(String(exchangeRate));
  const [rateMsg, setRateMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [generalSettings, setGeneralSettings] = useState({
    bot_name: '',
    min_deposit: '',
    min_withdrawal: '',
    deposit_message: '',
    withdrawal_message: ''
  });

  const [notificationSettings, setNotificationSettings] = useState({
    deposit_approved_message: '',
    deposit_rejected_message: '',
    withdrawal_approved_message: '',
    withdrawal_rejected_message: ''
  });
  const [notificationMsg, setNotificationMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [generalMsg, setGeneralMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [pwForm, setPwForm] = useState({ current: '', newPw: '', confirm: '' });
  const [pwShow, setPwShow] = useState({ current: false, newPw: false, confirm: false });
  const [pwMsg, setPwMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [pwLoading, setPwLoading] = useState(false);

  const loadGeneralSettings = useCallback(async () => {
    const { data } = await supabase
      .from('app_settings')
      .select('key,value')
      .in('key', ['bot_name', 'min_deposit', 'min_withdrawal', 'deposit_message', 'withdrawal_message', 'deposit_approved_message', 'deposit_rejected_message', 'withdrawal_approved_message', 'withdrawal_rejected_message']);

    if (data) {
      const map: Record<string, string> = {};
      data.forEach(s => (map[s.key] = s.value));

      setGeneralSettings({
        bot_name: map.bot_name || '',
        min_deposit: map.min_deposit || '',
        min_withdrawal: map.min_withdrawal || '',
        deposit_message: map.deposit_message || '',
        withdrawal_message: map.withdrawal_message || ''
      });

      setNotificationSettings({
        deposit_approved_message: map.deposit_approved_message || '✅ تمت الموافقة على إيداعك!\n\n💰 المبلغ: {amount_syp} ل.س\n🏦 المحفظة: {wallet_name}\n📊 رقم العملية: {operation_number}\n\nتم إضافة المبلغ إلى رصيدك.',
        deposit_rejected_message: map.deposit_rejected_message || '❌ تم رفض إيداعك\n\n💰 المبلغ: {amount_syp} ل.س\n🏦 المحفظة: {wallet_name}\n📊 رقم العملية: {operation_number}\n\nيرجى التواصل مع الدعم للمزيد من المعلومات.',
        withdrawal_approved_message: map.withdrawal_approved_message || '✅ تمت الموافقة على طلب السحب!\n\n💰 المبلغ: {amount_syp} ل.س\n📊 رقم العملية: {operation_number}\n\nتم معالجة طلبك وسيتم إرسال المبلغ قريباً.',
        withdrawal_rejected_message: map.withdrawal_rejected_message || '❌ تم رفض طلب السحب\n\n💰 المبلغ: {amount_syp} ل.س\n📊 رقم العملية: {operation_number}\n\nيرجى التواصل مع الدعم للمزيد من المعلومات.'
      });
    }
  }, []);

  useEffect(() => {
    loadGeneralSettings();
    loadBotStatus();
  }, [loadGeneralSettings]);

  useEffect(() => {
    setRateInput(String(exchangeRate));
  }, [exchangeRate]);

  const loadBotStatus = async () => {
    try {
      const { data } = await supabase
        .from('app_settings')
        .select('value')
        .eq('key', 'bot_status')
        .single();

      if (data) {
        setBotStatus(data.value as 'active' | 'paused');
      }
    } catch (error) {
      console.error('Error loading bot status:', error);
    }
  };

  const toggleBotStatus = async () => {
    try {
      const newStatus = botStatus === 'active' ? 'paused' : 'active';
      
      const { error } = await supabase
        .from('app_settings')
        .upsert({ 
          key: 'bot_status', 
          value: newStatus,
          updated_at: new Date().toISOString()
        }, { onConflict: 'key' });

      if (error) throw error;

      setBotStatus(newStatus);
      setBotStatusMsg({
        type: 'success',
        text: newStatus === 'paused' 
          ? (language === 'ar' ? 'تم إيقاف البوت بنجاح' : 'Bot paused successfully')
          : (language === 'ar' ? 'تم تشغيل البوت بنجاح' : 'Bot resumed successfully')
      });

      setTimeout(() => setBotStatusMsg(null), 3000);
    } catch (error) {
      console.error('Error toggling bot status:', error);
      setBotStatusMsg({
        type: 'error',
        text: language === 'ar' ? 'فشل تغيير حالة البوت' : 'Failed to change bot status'
      });
      setTimeout(() => setBotStatusMsg(null), 3000);
    }
  };

  const saveRate = async () => {
    const val = Number(rateInput);

    if (isNaN(val) || val <= 0) {
      setRateMsg({
        type: 'error',
        text: language === 'ar' ? 'سعر صرف غير صالح' : 'Invalid exchange rate'
      });
      return;
    }

    const { error } = await supabase
      .from('settings')
      .upsert({ key: 'usd_rate', value: val.toString() }, { onConflict: 'key' });

    if (error) {
      setRateMsg({ type: 'error', text: error.message });
      return;
    }

    setRateMsg({
      type: 'success',
      text: language === 'ar' ? 'تم حفظ سعر الصرف' : 'Saved'
    });

    // Refresh exchange rate in context to update UI
    await refreshExchangeRate();

    setTimeout(() => setRateMsg(null), 3000);
  };

  const saveGeneralSettings = async () => {
    try {
      const upserts = Object.entries(generalSettings).map(([key, value]) => ({
        key,
        value,
        updated_at: new Date().toISOString()
      }));

      await supabase.from('app_settings').upsert(upserts, { onConflict: 'key' });

      setGeneralMsg({
        type: 'success',
        text: language === 'ar' ? 'تم حفظ الإعدادات' : 'Settings saved'
      });

      setTimeout(() => setGeneralMsg(null), 3000);
    } catch {
      setGeneralMsg({
        type: 'error',
        text: language === 'ar' ? 'حدث خطأ' : 'An error occurred'
      });
    }
  };

  const saveNotificationSettings = async () => {
    try {
      const upserts = Object.entries(notificationSettings).map(([key, value]) => ({
        key,
        value,
        updated_at: new Date().toISOString()
      }));

      await supabase.from('app_settings').upsert(upserts, { onConflict: 'key' });

      setNotificationMsg({
        type: 'success',
        text: language === 'ar' ? 'تم حفظ رسائل الإشعارات' : 'Notification messages saved'
      });

      setTimeout(() => setNotificationMsg(null), 3000);
    } catch {
      setNotificationMsg({
        type: 'error',
        text: language === 'ar' ? 'حدث خطأ' : 'An error occurred'
      });
    }
  };

  const changePassword = async () => {
    if (!pwForm.current || !pwForm.newPw) return;

    if (pwForm.newPw !== pwForm.confirm) {
      setPwMsg({
        type: 'error',
        text: language === 'ar' ? 'كلمات المرور غير متطابقة' : 'Passwords do not match'
      });
      return;
    }

    if (pwForm.newPw.length < 8) {
      setPwMsg({
        type: 'error',
        text: language === 'ar' ? 'كلمة المرور يجب أن تكون 8 أحرف على الأقل' : 'Password must be at least 8 characters'
      });
      return;
    }

    setPwLoading(true);

    const { error } = await supabase.auth.updateUser({
      password: pwForm.newPw
    });

    if (error) {
      setPwMsg({ type: 'error', text: error.message });
    } else {
      setPwMsg({
        type: 'success',
        text: language === 'ar' ? 'تم تغيير كلمة المرور بنجاح' : 'Password changed successfully'
      });

      setPwForm({ current: '', newPw: '', confirm: '' });
    }

    setPwLoading(false);
  };

  const tabsCls = (tab: SettingsTab) =>
    `px-4 py-2.5 text-sm font-medium rounded-xl transition-all
    ${
      activeTab === tab
        ? 'bg-blue-600 text-white'
        : isDark
        ? 'text-slate-400 hover:text-white hover:bg-slate-700'
        : 'text-slate-600 hover:bg-slate-100'
    }`;

  const inputCls = `w-full px-4 py-3 rounded-xl text-sm border outline-none transition-colors
    ${
      isDark
        ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500 focus:border-blue-500'
        : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-blue-500'
    }`;

  const labelCls = `block text-xs font-medium mb-1.5 ${
    isDark ? 'text-slate-400' : 'text-slate-500'
  }`;

  const cardCls = `rounded-2xl border p-5 space-y-4 ${
    isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'
  }`;

  const msgEl = (msg: { type: 'success' | 'error'; text: string } | null) =>
    msg ? (
      <div
        className={`flex items-center gap-2 p-3 rounded-xl text-sm ${
          msg.type === 'success'
            ? 'bg-emerald-500/15 text-emerald-400'
            : 'bg-red-500/15 text-red-400'
        }`}
      >
        {msg.type === 'success' ? <CheckCircle size={14} /> : <XCircle size={14} />}
        {msg.text}
      </div>
    ) : null;

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div
        className={`flex gap-2 p-1.5 rounded-2xl border ${
          isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'
        }`}
      >
        <button className={tabsCls('general')} onClick={() => setActiveTab('general')}>
          <span className="flex items-center gap-2">
            <Globe size={14} />
            {t(language, 'generalSettings')}
          </span>
        </button>

        <button className={tabsCls('security')} onClick={() => setActiveTab('security')}>
          <span className="flex items-center gap-2">
            <Shield size={14} />
            {t(language, 'securitySettings')}
          </span>
        </button>

        <button className={tabsCls('bot')} onClick={() => setActiveTab('bot')}>
          <span className="flex items-center gap-2">
            {botStatus === 'active' ? <Pause size={14} /> : <Play size={14} />}
            {language === 'ar' ? 'التحكم بالبوت' : 'Bot Control'}
          </span>
        </button>
      </div>

      {/* GENERAL */}
      {activeTab === 'general' && (
        <div className="space-y-4">
          <div className={cardCls}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-800'}`}>
              <Palette size={14} className="text-blue-400" /> {t(language, 'theme')}
            </h3>

            <div className="grid grid-cols-2 gap-3">
              {(['dark', 'light'] as const).map(th => (
                <button
                  key={th}
                  onClick={() => setTheme(th)}
                  className={`py-3 rounded-xl border text-sm font-medium transition-all
                  ${
                    theme === th
                      ? 'border-blue-500 bg-blue-600/10 text-blue-400'
                      : isDark
                      ? 'border-slate-600 text-slate-400 hover:border-slate-500'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  {th === 'dark' ? (language === 'ar' ? 'داكن' : 'Dark') : (language === 'ar' ? 'فاتح' : 'Light')}
                </button>
              ))}
            </div>
          </div>

          <div className={cardCls}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-800'}`}>
              <Globe size={14} className="text-blue-400" /> {t(language, 'language')}
            </h3>

            <div className="grid grid-cols-2 gap-3">
              {(['ar', 'en'] as const).map(lang => (
                <button
                  key={lang}
                  onClick={() => setLanguage(lang)}
                  className={`py-3 rounded-xl border text-sm font-medium transition-all
                  ${
                    language === lang
                      ? 'border-blue-500 bg-blue-600/10 text-blue-400'
                      : isDark
                      ? 'border-slate-600 text-slate-400 hover:border-slate-500'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  {lang === 'ar' ? 'العربية' : 'English'}
                </button>
              ))}
            </div>
          </div>

          <div className={cardCls}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-800'}`}>
              <DollarSign size={14} className="text-amber-400" /> {t(language, 'exchangeRateSetting')}
            </h3>

            <input
              type="number"
              value={rateInput}
              onChange={e => setRateInput(e.target.value)}
              className={inputCls}
            />

            {msgEl(rateMsg)}

            <button
              onClick={saveRate}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl"
            >
              <Save size={14} /> {t(language, 'save')}
            </button>
          </div>

          <div className={cardCls}>
            <h3 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-slate-800'}`}>
              {language === 'ar' ? 'إعدادات البوت' : 'Bot Settings'}
            </h3>

            <div className="space-y-4">
              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'اسم البوت (يظهر في الرسائل)' : 'Bot Name (appears in messages)'}
                </label>
                <input
                  value={generalSettings.bot_name}
                  onChange={e => setGeneralSettings(s => ({ ...s, bot_name: e.target.value }))}
                  placeholder={language === 'ar' ? 'مثال: بوت الدفع الآمن' : 'e.g. Secure Payment Bot'}
                  className={inputCls}
                />
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'الحد الأدنى للإيداع (ل.س)' : 'Minimum Deposit (SYP)'}
                </label>
                <input
                  type="number"
                  value={generalSettings.min_deposit}
                  onChange={e => setGeneralSettings(s => ({ ...s, min_deposit: e.target.value }))}
                  placeholder="5000"
                  className={inputCls}
                />
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'الحد الأدنى للسحب (ل.س)' : 'Minimum Withdrawal (SYP)'}
                </label>
                <input
                  type="number"
                  value={generalSettings.min_withdrawal}
                  onChange={e => setGeneralSettings(s => ({ ...s, min_withdrawal: e.target.value }))}
                  placeholder="10000"
                  className={inputCls}
                />
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'رسالة الإيداع (تظهر للمستخدم عند طلب الإيداع)' : 'Deposit Message (shown when user requests deposit)'}
                </label>
                <textarea
                  value={generalSettings.deposit_message}
                  onChange={e => setGeneralSettings(s => ({ ...s, deposit_message: e.target.value }))}
                  placeholder={language === 'ar' ? 'ارسل المال ثم ادخل رقم العملية...' : 'Send money then enter operation number...'}
                  rows={4}
                  className={inputCls}
                />
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'رسالة السحب (تظهر للمستخدم عند طلب السحب)' : 'Withdrawal Message (shown when user requests withdrawal)'}
                </label>
                <textarea
                  value={generalSettings.withdrawal_message}
                  onChange={e => setGeneralSettings(s => ({ ...s, withdrawal_message: e.target.value }))}
                  placeholder={language === 'ar' ? 'أدخل رقم حسابك ورقم المبلغ...' : 'Enter your account number and amount...'}
                  rows={4}
                  className={inputCls}
                />
              </div>
            </div>

            {msgEl(generalMsg)}

            <button onClick={saveGeneralSettings} className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl">
              <Save size={14} /> {t(language, 'save')}
            </button>
          </div>

          {/* Notification Messages */}
          <div className={cardCls}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-800'}`}>
              <span className="text-lg">🔔</span> {language === 'ar' ? 'رسائل الإشعارات (تليجرام)' : 'Telegram Notifications'}
            </h3>

            <div className="space-y-4">
              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'رسالة الموافقة على الإيداع' : 'Deposit Approved Message'}
                </label>
                <textarea
                  value={notificationSettings.deposit_approved_message}
                  onChange={e => setNotificationSettings(s => ({ ...s, deposit_approved_message: e.target.value }))}
                  className={inputCls}
                  rows={5}
                  placeholder="{amount_syp} {wallet_name} {operation_number}"
                />
                <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                  {language === 'ar'
                    ? 'المتغيرات: {amount_syp} = المبلغ, {wallet_name} = المحفظة, {operation_number} = رقم العملية'
                    : 'Variables: {amount_syp} = amount, {wallet_name} = wallet, {operation_number} = operation number'}
                </p>
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'رسالة رفض الإيداع' : 'Deposit Rejected Message'}
                </label>
                <textarea
                  value={notificationSettings.deposit_rejected_message}
                  onChange={e => setNotificationSettings(s => ({ ...s, deposit_rejected_message: e.target.value }))}
                  className={inputCls}
                  rows={5}
                  placeholder="{amount_syp} {wallet_name} {operation_number}"
                />
                <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                  {language === 'ar'
                    ? 'المتغيرات: {amount_syp} = المبلغ, {wallet_name} = المحفظة, {operation_number} = رقم العملية'
                    : 'Variables: {amount_syp} = amount, {wallet_name} = wallet, {operation_number} = operation number'}
                </p>
              </div>

              <div className="border-t pt-4 border-slate-700/30">
                <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                  {language === 'ar' ? '🔴 رسائل السحب' : '🔴 Withdrawal Messages'}
                </h4>
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'رسالة الموافقة على السحب' : 'Withdrawal Approved Message'}
                </label>
                <textarea
                  value={notificationSettings.withdrawal_approved_message}
                  onChange={e => setNotificationSettings(s => ({ ...s, withdrawal_approved_message: e.target.value }))}
                  className={inputCls}
                  rows={5}
                  placeholder="{amount_syp} {operation_number}"
                />
                <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                  {language === 'ar'
                    ? 'المتغيرات: {amount_syp} = المبلغ, {operation_number} = رقم العملية'
                    : 'Variables: {amount_syp} = amount, {operation_number} = operation number'}
                </p>
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'رسالة رفض السحب' : 'Withdrawal Rejected Message'}
                </label>
                <textarea
                  value={notificationSettings.withdrawal_rejected_message}
                  onChange={e => setNotificationSettings(s => ({ ...s, withdrawal_rejected_message: e.target.value }))}
                  className={inputCls}
                  rows={5}
                  placeholder="{amount_syp} {operation_number}"
                />
                <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                  {language === 'ar'
                    ? 'المتغيرات: {amount_syp} = المبلغ, {operation_number} = رقم العملية'
                    : 'Variables: {amount_syp} = amount, {operation_number} = operation number'}
                </p>
              </div>
            </div>

            {msgEl(notificationMsg)}

            <button onClick={saveNotificationSettings} className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-xl">
              <Save size={14} /> {language === 'ar' ? 'حفظ رسائل الإشعارات' : 'Save Notification Messages'}
            </button>
          </div>
        </div>
      )}

      {/* SECURITY */}
      {activeTab === 'security' && (
        <div className="space-y-4">
          <div className={cardCls}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-800'}`}>
              <Shield size={14} /> {t(language, 'changeAdminPassword')}
            </h3>

            <div className="space-y-4">
              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'كلمة المرور الحالية' : 'Current Password'}
                </label>
                <div className="relative">
                  <input
                    type={pwShow.current ? 'text' : 'password'}
                    value={pwForm.current}
                    onChange={e => setPwForm(f => ({ ...f, current: e.target.value }))}
                    placeholder={language === 'ar' ? 'أدخل كلمة المرور الحالية' : 'Enter your current password'}
                    className={`${inputCls} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setPwShow(s => ({ ...s, current: !s.current }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {pwShow.current ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'كلمة المرور الجديدة' : 'New Password'}
                </label>
                <div className="relative">
                  <input
                    type={pwShow.newPw ? 'text' : 'password'}
                    value={pwForm.newPw}
                    onChange={e => setPwForm(f => ({ ...f, newPw: e.target.value }))}
                    placeholder={language === 'ar' ? 'أدخل كلمة المرور الجديدة (8 أحرف على الأقل)' : 'Enter new password (min 8 characters)'}
                    className={`${inputCls} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setPwShow(s => ({ ...s, newPw: !s.newPw }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {pwShow.newPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label className={labelCls}>
                  {language === 'ar' ? 'تأكيد كلمة المرور الجديدة' : 'Confirm New Password'}
                </label>
                <div className="relative">
                  <input
                    type={pwShow.confirm ? 'text' : 'password'}
                    value={pwForm.confirm}
                    onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
                    placeholder={language === 'ar' ? 'أعد إدخال كلمة المرور الجديدة' : 'Re-enter new password'}
                    className={`${inputCls} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setPwShow(s => ({ ...s, confirm: !s.confirm }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {pwShow.confirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            </div>

            {msgEl(pwMsg)}

            <button
              onClick={changePassword}
              disabled={pwLoading}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl"
            >
              <Shield size={14} /> Save
            </button>
          </div>
        </div>
      )}

      {/* BOT CONTROL */}
      {activeTab === 'bot' && (
        <div className="space-y-4">
          <div className={cardCls}>
            <h3 className={`text-sm font-semibold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-800'}`}>
              {botStatus === 'active' ? <Play size={14} className="text-emerald-400" /> : <Pause size={14} className="text-red-400" />}
              {language === 'ar' ? 'حالة البوت' : 'Bot Status'}
            </h3>

            <div className={`p-6 rounded-xl ${botStatus === 'active' ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-lg font-semibold ${botStatus === 'active' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {botStatus === 'active' 
                      ? (language === 'ar' ? 'البوت يعمل حالياً' : 'Bot is currently running')
                      : (language === 'ar' ? 'البوت متوقف حالياً' : 'Bot is currently paused')
                    }
                  </p>
                  <p className={`text-sm mt-1 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                    {botStatus === 'active'
                      ? (language === 'ar' ? 'يمكن للمستخدمين استخدام جميع وظائف البوت' : 'Users can access all bot functions')
                      : (language === 'ar' ? 'المستخدمون سيرون رسالة صيانة عند محاولة استخدام البوت' : 'Users will see maintenance message when trying to use the bot')
                    }
                  </p>
                </div>
                <div className={`px-4 py-2 rounded-full text-sm font-medium ${
                  botStatus === 'active' 
                    ? 'bg-emerald-500 text-white' 
                    : 'bg-red-500 text-white'
                }`}>
                  {botStatus === 'active' 
                    ? (language === 'ar' ? 'يعمل' : 'Running')
                    : (language === 'ar' ? 'متوقف' : 'Paused')
                  }
                </div>
              </div>
            </div>

            {msgEl(botStatusMsg)}

            <div className="flex gap-3">
              <button
                onClick={toggleBotStatus}
                disabled={false}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  botStatus === 'active'
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-emerald-600 text-white hover:bg-emerald-700'
                }`}
              >
                {botStatus === 'active' ? <Pause size={16} /> : <Play size={16} />}
                {botStatus === 'active' 
                  ? (language === 'ar' ? 'إيقاف البوت' : 'Pause Bot')
                  : (language === 'ar' ? 'تشغيل البوت' : 'Resume Bot')
                }
              </button>
            </div>
          </div>

          <div className={cardCls}>
            <h3 className={`text-sm font-semibold mb-3 ${isDark ? 'text-white' : 'text-slate-800'}`}>
              {language === 'ar' ? 'معلومات إضافية' : 'Additional Information'}
            </h3>
            <div className="space-y-2">
              <div className={`p-3 rounded-lg ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
                <p className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                  <span className="font-medium">{language === 'ar' ? 'ملاحظة:' : 'Note:'}</span> {language === 'ar' 
                    ? 'عند إيقاف البوت، سيتم عرض رسالة مخصصة للمستخدمين تفيد بأن البوت في وضع الصيانة.'
                    : 'When the bot is paused, users will see a custom maintenance message.'
                  }
                </p>
              </div>
              <div className={`p-3 rounded-lg ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
                <p className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                  <span className="font-medium">{language === 'ar' ? 'تأثير:' : 'Impact:'}</span> {language === 'ar' 
                    ? 'إيقاف البوت يمنع المستخدمين من إجراء المعاملات والوصول إلى وظائف البوت الأخرى.'
                    : 'Pausing the bot prevents users from making transactions and accessing other bot functions.'
                  }
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}