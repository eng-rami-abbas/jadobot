import { useState, useEffect } from 'react';
import { Eye, EyeOff, Lock, Mail, Bot, AlertCircle, Clock } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';

const LOCKOUT_DURATION = 15 * 60 * 1000;

export default function LoginPage() {
  const { login, isLockedOut, loginAttempts } = useApp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (!isLockedOut) return;
    const lockoutTime = Number(localStorage.getItem('lockoutTime') || '0');
    const updateCountdown = () => {
      const remaining = lockoutTime + LOCKOUT_DURATION - Date.now();
      if (remaining <= 0) { setCountdown(0); return; }
      setCountdown(Math.ceil(remaining / 1000));
    };
    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [isLockedOut]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError('يرجى إدخال البريد الإلكتروني وكلمة المرور'); return; }
    setLoading(true);
    setError('');
    const { error: err } = await login(email, password);
    if (err) setError(err);
    setLoading(false);
  };

  const mins = Math.floor(countdown / 60);
  const secs = countdown % 60;

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -start-40 w-80 h-80 bg-blue-600/8 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -end-40 w-80 h-80 bg-blue-600/6 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/4 rounded-full blur-3xl" />
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.02) 1px, transparent 0)`,
          backgroundSize: '40px 40px',
        }} />
      </div>

      <div className="w-full max-w-sm relative z-10">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-2xl shadow-blue-500/30">
            <Bot size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1">لوحة التحكم</h1>
          <p className="text-slate-400 text-sm">تسجيل الدخول للإدارة</p>
        </div>

        <div className="bg-slate-900 rounded-2xl border border-slate-700/50 p-6 shadow-2xl">
          {isLockedOut && countdown > 0 ? (
            <div className="text-center space-y-4">
              <div className="w-14 h-14 bg-red-500/15 rounded-2xl flex items-center justify-center mx-auto">
                <Clock size={28} className="text-red-400" />
              </div>
              <p className="text-red-400 font-semibold">تم تجاوز الحد الأقصى للمحاولات</p>
              <p className="text-slate-400 text-sm">يرجى الانتظار</p>
              <div className="bg-slate-800 rounded-xl py-4 px-6">
                <p className="text-3xl font-bold text-white font-mono">
                  {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
                </p>
              </div>
              <p className="text-slate-500 text-xs">سيتم إلغاء القفل تلقائياً بعد انتهاء المؤقت</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">البريد الإلكتروني</label>
                <div className="relative">
                  <Mail size={15} className="absolute top-1/2 -translate-y-1/2 start-3.5 text-slate-500 pointer-events-none" />
                  <input
                    type="email"
                    value={email}
                    onChange={e => { setEmail(e.target.value); setError(''); }}
                    className="w-full ps-10 pe-4 py-3 bg-slate-800 border border-slate-700 text-white rounded-xl text-sm outline-none focus:border-blue-500 transition-colors placeholder-slate-500"
                    placeholder="admin@example.com"
                    autoComplete="email"
                    disabled={loading}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">كلمة المرور</label>
                <div className="relative">
                  <Lock size={15} className="absolute top-1/2 -translate-y-1/2 start-3.5 text-slate-500 pointer-events-none" />
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => { setPassword(e.target.value); setError(''); }}
                    className="w-full ps-10 pe-10 py-3 bg-slate-800 border border-slate-700 text-white rounded-xl text-sm outline-none focus:border-blue-500 transition-colors placeholder-slate-500"
                    placeholder="••••••••"
                    autoComplete="current-password"
                    disabled={loading}
                  />
                  <button type="button" onClick={() => setShowPw(v => !v)}
                    className="absolute top-1/2 -translate-y-1/2 end-3.5 text-slate-500 hover:text-slate-300 transition-colors">
                    {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
                  <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
                  <p className="text-red-400 text-xs">{error}</p>
                </div>
              )}

              {loginAttempts > 0 && !error && (
                <p className="text-amber-400 text-xs text-center">
                  {5 - loginAttempts} {loginAttempts >= 4 ? 'محاولة أخيرة!' : 'محاولات متبقية'}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className={`w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-all duration-200
                  shadow-lg shadow-blue-500/25 ${loading ? 'opacity-70 cursor-not-allowed' : 'hover:shadow-blue-500/40 hover:-translate-y-0.5'}`}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    جاري التحقق...
                  </span>
                ) : 'تسجيل الدخول'}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          محمي بـ Supabase Auth · JWT · Rate Limiting
        </p>
      </div>
    </div>
  );
}
