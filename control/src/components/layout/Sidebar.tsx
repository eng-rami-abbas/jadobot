import { LayoutDashboard, Users, MessageSquare, ArrowDownToLine, ArrowUpFromLine, Settings, LogOut, Bot, X, Gift, Wallet, CreditCard, Megaphone, RotateCw, Palette, TrendingUp } from 'lucide-react';
import  { useApp } from '../../contexts/GlobalContext';
import type { Page } from '../../types';

const navItems: { key: Page; icon: React.ElementType; labelAr: string; labelEn: string }[] = [
  { key: 'dashboard', icon: LayoutDashboard, labelAr: 'لوحة التحكم', labelEn: 'Dashboard' },
  { key: 'users', icon: Users, labelAr: 'المستخدمون', labelEn: 'Users' },
  { key: 'messages', icon: MessageSquare, labelAr: 'الرسائل', labelEn: 'Messages' },
  { key: 'events', icon: Settings, labelAr: 'الأحداث', labelEn: 'Events' },
  { key: 'deposits', icon: ArrowDownToLine, labelAr: 'سجلات الإيداع', labelEn: 'Deposits' },
  { key: 'withdrawals', icon: ArrowUpFromLine, labelAr: 'سجلات السحب', labelEn: 'Withdrawals' },
  { key: 'wallets', icon: Wallet, labelAr: 'المحافظ', labelEn: 'Wallets' },
  { key: 'withdrawal-methods', icon: CreditCard, labelAr: 'طرق السحب', labelEn: 'Withdrawal Methods' },
  { key: 'gift-codes', icon: Gift, labelAr: 'أكواد الهدية', labelEn: 'Gift Codes' },
  { key: 'broadcast', icon: Megaphone, labelAr: 'رسائل جماعية', labelEn: 'Broadcast' },
  { key: 'settings', icon: Settings, labelAr: 'الإعدادات', labelEn: 'Settings' },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { 
    language, currentPage, setCurrentPage, logout, theme,
    // 🔥 نقاط حمراء
    newDepositsCount, newWithdrawalsCount, newMessagesCount,
    clearNewDeposits, clearNewWithdrawals, clearNewMessages
  } = useApp();
  const isDark = theme === 'dark';

  const handleNav = (page: Page) => {
    // 🔥 مسح النقطة الحمراء عند الدخول للصفحة
    if (page === 'deposits') clearNewDeposits();
    if (page === 'withdrawals') clearNewWithdrawals();
    if (page === 'messages') clearNewMessages();
    
    setCurrentPage(page);
    onClose();
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside className={`
        fixed top-0 ${language === 'ar' ? 'right-0' : 'left-0'} h-full z-30 w-64 flex flex-col
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : (language === 'ar' ? 'translate-x-full' : '-translate-x-full')}
        lg:translate-x-0 lg:static lg:z-auto
        ${isDark ? 'bg-slate-900 border-slate-700/50' : 'bg-white border-slate-200'}
        border-e shadow-2xl
      `}>
        <div className={`flex items-center justify-between px-5 py-5 border-b ${isDark ? 'border-slate-700/50' : 'border-slate-100'}`}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Bot size={20} className="text-white" />
            </div>
            <div>
              <p className={`font-bold text-sm ${isDark ? 'text-white' : 'text-slate-800'}`}>
                {language === 'ar' ? 'لوحة التحكم' : 'Admin Panel'}
              </p>
              <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Bot Manager</p>
            </div>
          </div>
          <button onClick={onClose} className={`lg:hidden p-1.5 rounded-lg ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-700' : 'text-slate-500 hover:bg-slate-100'}`}>
            <X size={16} />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ key, icon: Icon, labelAr, labelEn }) => {
            const isActive = currentPage === key;
            const label = language === 'ar' ? labelAr : labelEn;
            return (
              <button
                key={key}
                onClick={() => handleNav(key)}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                  transition-all duration-200 group
                  ${isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                    : isDark
                      ? 'text-slate-400 hover:text-white hover:bg-slate-800'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }
                `}
              >
                <Icon size={18} className={isActive ? 'text-white' : isDark ? 'text-slate-400 group-hover:text-white' : 'text-slate-500'} />
                <span>{label}</span>
                {/* 🔥 النقاط الحمراء للإشعارات الجديدة */}
                {!isActive && key === 'messages' && newMessagesCount > 0 && (
                  <span className="ms-auto flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-bold bg-red-500 text-white rounded-full">
                    {newMessagesCount > 9 ? '9+' : newMessagesCount}
                  </span>
                )}
                {!isActive && key === 'deposits' && newDepositsCount > 0 && (
                  <span className="ms-auto flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-bold bg-red-500 text-white rounded-full">
                    {newDepositsCount > 9 ? '9+' : newDepositsCount}
                  </span>
                )}
                {!isActive && key === 'withdrawals' && newWithdrawalsCount > 0 && (
                  <span className="ms-auto flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-bold bg-red-500 text-white rounded-full">
                    {newWithdrawalsCount > 9 ? '9+' : newWithdrawalsCount}
                  </span>
                )}
                {isActive && <div className="ms-auto w-1.5 h-1.5 rounded-full bg-white/70" />}
              </button>
            );
          })}
        </nav>

        <div className={`px-3 pb-4 border-t ${isDark ? 'border-slate-700/50' : 'border-slate-100'} pt-3`}>
          <button
            onClick={logout}
            className={`
              w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
              transition-all duration-200
              ${isDark ? 'text-red-400 hover:text-red-300 hover:bg-red-500/10' : 'text-red-500 hover:text-red-600 hover:bg-red-50'}
            `}
          >
            <LogOut size={18} />
            <span>{language === 'ar' ? 'تسجيل الخروج' : 'Logout'}</span>
          </button>
        </div>
      </aside>
    </>
  );
}