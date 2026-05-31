import { useState, useRef, useEffect } from 'react';
import { Menu, Bell, CheckCheck, Clock, TrendingDown, TrendingUp, UserPlus, MessageCircle, Cpu } from 'lucide-react';
import { useApp } from '../../contexts/GlobalContext';
import { t } from '../../lib/i18n';
import type { Notification } from '../../types';

const pageLabels: Record<string, { ar: string; en: string }> = {
  dashboard: { ar: 'لوحة التحكم', en: 'Dashboard' },
  users: { ar: 'المستخدمون', en: 'Users' },
  messages: { ar: 'الرسائل', en: 'Messages' },
  deposits: { ar: 'سجلات الإيداع', en: 'Deposit Records' },
  withdrawals: { ar: 'سجلات السحب', en: 'Withdrawal Records' },
  settings: { ar: 'الإعدادات', en: 'Settings' },
};

const notifIcon = (type: Notification['type']) => {
  const cls = 'w-4 h-4';
  if (type === 'deposit') return <TrendingDown className={`${cls} text-emerald-400`} />;
  if (type === 'withdrawal') return <TrendingUp className={`${cls} text-red-400`} />;
  if (type === 'user') return <UserPlus className={`${cls} text-blue-400`} />;
  if (type === 'message') return <MessageCircle className={`${cls} text-amber-400`} />;
  return <Cpu className={`${cls} text-slate-400`} />;
};

const notifBg = (type: Notification['type']) => {
  if (type === 'deposit') return 'bg-emerald-500/10';
  if (type === 'withdrawal') return 'bg-red-500/10';
  if (type === 'user') return 'bg-blue-500/10';
  if (type === 'message') return 'bg-amber-500/10';
  return 'bg-slate-500/10';
};

function timeAgo(date: string, lang: 'ar' | 'en'): string {
  const diff = Date.now() - new Date(date).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (lang === 'ar') {
    if (mins < 1) return 'الآن';
    if (mins < 60) return `منذ ${mins} د`;
    if (hours < 24) return `منذ ${hours} س`;
    return `منذ ${days} ي`;
  }
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

interface HeaderProps {
  onMenuClick: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { theme, language, currentPage, notifications, unreadCount, markAllRead, markRead } = useApp();
  const isDark = theme === 'dark';
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const pageLabel = pageLabels[currentPage]?.[language] || '';

  return (
    <header className={`
      h-16 flex items-center justify-between px-4 lg:px-6 shrink-0 border-b
      ${isDark ? 'bg-slate-900/95 border-slate-700/50' : 'bg-white/95 border-slate-200'}
      backdrop-blur-md sticky top-0 z-10
    `}>
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className={`lg:hidden p-2 rounded-lg transition-colors ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-500 hover:bg-slate-100'}`}
        >
          <Menu size={20} />
        </button>
        <div>
          <h1 className={`text-base font-semibold ${isDark ? 'text-white' : 'text-slate-800'}`}>{pageLabel}</h1>
        </div>
      </div>

      <div className="flex items-center gap-2" ref={notifRef}>
        <div className="relative">
          <button
            onClick={() => setNotifOpen(v => !v)}
            className={`relative p-2 rounded-xl transition-all duration-200
              ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-500 hover:bg-slate-100'}
              ${notifOpen ? (isDark ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-900') : ''}
            `}
          >
            <Bell size={20} />
            {unreadCount > 0 && (
              <span className="absolute top-1 end-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-lg shadow-red-500/40">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className={`
              absolute top-full mt-2 w-80 rounded-2xl shadow-2xl border overflow-hidden z-50
              ${language === 'ar' ? 'left-0' : 'right-0'}
              ${isDark ? 'bg-slate-900 border-slate-700/50' : 'bg-white border-slate-200'}
            `}>
              <div className={`flex items-center justify-between px-4 py-3 border-b ${isDark ? 'border-slate-700/50' : 'border-slate-100'}`}>
                <span className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-slate-800'}`}>
                  {t(language, 'notifications')}
                  {unreadCount > 0 && <span className="ms-2 px-1.5 py-0.5 text-xs bg-blue-600 text-white rounded-full">{unreadCount}</span>}
                </span>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllRead}
                    className={`flex items-center gap-1 text-xs transition-colors ${isDark ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'}`}
                  >
                    <CheckCheck size={14} />
                    {t(language, 'markAllRead')}
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto">
                {(() => {
                  // 🔥 تصفية الإشعارات - إخفاء الرسائل، إظهار فقط الإيداعات والسحوبات
                  const filteredNotifications = notifications.filter(n => n.type === 'deposit' || n.type === 'withdrawal');
                  
                  if (filteredNotifications.length === 0) {
                    return (
                      <div className={`py-10 text-center text-sm ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                        {t(language, 'noNotifications')}
                      </div>
                    );
                  }
                  
                  return filteredNotifications.map(n => (
                    <button
                      key={n.id}
                      onClick={() => markRead(n.id)}
                      className={`w-full text-start px-4 py-3 flex items-start gap-3 transition-colors border-b last:border-0
                        ${isDark ? 'border-slate-700/30 hover:bg-slate-800' : 'border-slate-50 hover:bg-slate-50'}
                        ${!n.is_read ? (isDark ? 'bg-blue-500/5' : 'bg-blue-50/50') : ''}
                      `}
                    >
                      <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center mt-0.5 ${notifBg(n.type)}`}>
                        {notifIcon(n.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs font-semibold truncate ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>{n.title}</p>
                        <p className={`text-xs truncate mt-0.5 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{n.body}</p>
                        <div className={`flex items-center gap-1 mt-1 text-[10px] ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                          <Clock size={10} />
                          {timeAgo(n.created_at, language)}
                          {!n.is_read && <span className="ms-1 w-1.5 h-1.5 rounded-full bg-blue-500 inline-block" />}
                        </div>
                      </div>
                    </button>
                  ));
                })()}
              </div>
            </div>
          )}
        </div>

        <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl ${isDark ? 'bg-slate-800' : 'bg-slate-100'}`}>
          <div className={`w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse`} />
          <span className={`text-xs font-medium ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
            {language === 'ar' ? 'متصل' : 'Online'}
          </span>
        </div>
      </div>
    </header>
  );
}
