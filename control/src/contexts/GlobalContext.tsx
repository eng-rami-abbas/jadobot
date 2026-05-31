import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from "../lib/supabase";
import type { Notification as AppNotification, Theme, Language, Page } from '../types';

interface AppContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  language: Language;
  setLanguage: (l: Language) => void;
  currentPage: Page;
  setCurrentPage: (p: Page) => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ error: string | null }>;
  logout: () => Promise<void>;
  notifications: AppNotification[];
  unreadCount: number;
  markAllRead: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  addNotification: (n: Omit<AppNotification, 'id' | 'created_at' | 'is_read'>) => void;
  exchangeRate: number;
  setExchangeRate: (r: number) => Promise<void>;
  refreshExchangeRate: () => Promise<void>;
  loginAttempts: number;
  isLockedOut: boolean;
  // 🔥 نقاط حمراء في السايدبار
  newDepositsCount: number;
  newWithdrawalsCount: number;
  newMessagesCount: number;
  clearNewDeposits: () => void;
  clearNewWithdrawals: () => void;
  clearNewMessages: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

const MAX_LOGIN_ATTEMPTS = 5;
const LOCKOUT_DURATION = 15 * 60 * 1000;

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => (localStorage.getItem('theme') as Theme) || 'dark');
  const [language, setLanguageState] = useState<Language>(() => (localStorage.getItem('language') as Language) || 'ar');
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [exchangeRate, setExchangeRateState] = useState(14500);
  const [loginAttempts, setLoginAttempts] = useState(() => Number(localStorage.getItem('loginAttempts') || '0'));
  const [lockoutTime, setLockoutTime] = useState(() => Number(localStorage.getItem('lockoutTime') || '0'));
  const notifChannelRef = useRef<ReturnType<typeof supabase.channel> | null>(null);

  const isLockedOut = lockoutTime > 0 && Date.now() < lockoutTime + LOCKOUT_DURATION;

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsAuthenticated(!!session);
      setIsLoading(false);
    });

    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsAuthenticated(!!session);
      setIsLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;

    supabase.from('app_settings')
      .select('key,value')
      .in('key', ['exchange_rate', 'language', 'theme'])
      .then(({ data }) => {
        if (data) {
          data.forEach(s => {
            if (s.key === 'exchange_rate') setExchangeRateState(Number(s.value));
            if (s.key === 'language') setLanguageState(s.value as Language);
            if (s.key === 'theme') setThemeState(s.value as Theme);
          });
        }
      });

    supabase.from('notifications')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(50)
      .then(({ data }) => {
        if (data) setNotifications(data as AppNotification[]);
      });
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const channel = supabase.channel('notifications_realtime')
      .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'notifications' },
        payload => {
          const newNotif = payload.new as AppNotification;

          setNotifications(prev => [newNotif, ...prev.slice(0, 49)]);

          if (window.Notification.permission === 'granted') {
            new window.Notification(newNotif.title, {
              body: newNotif.body
            });
          }
        }
      ).subscribe();

    notifChannelRef.current = channel;

    return () => { channel.unsubscribe(); };
  }, [isAuthenticated]);

  // 🔥 إشعارات السايدبار (نقاط حمراء)
  const [newDepositsCount, setNewDepositsCount] = useState(0);
  const [newWithdrawalsCount, setNewWithdrawalsCount] = useState(0);
  const [newMessagesCount, setNewMessagesCount] = useState(0);

  // 🔄 تحديث سعر الصرف
  const [exchangeRateKey, setExchangeRateKey] = useState(0);
  const refreshExchangeRate = useCallback(async () => {
    try {
      const { data } = await supabase
        .from('settings')
        .select('value')
        .eq('key', 'usd_rate')
        .single();

      if (data) {
        setExchangeRate(data.value);
        setExchangeRateKey(prev => prev + 1); // Force re-render
      }
    } catch (error) {
      console.error('Error refreshing exchange rate:', error);
    }
  }, []);

  // Realtime subscriptions for deposits, withdrawals, messages
  useEffect(() => {
    if (!isAuthenticated) return;

    const depositsChannel = supabase.channel('deposits_notifications')
      .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'transactions', filter: "type=eq.deposit" },
        async payload => {
          const tx = payload.new;
          console.log('[Realtime] New deposit:', tx);
          // إشعار في الهيدر
          await addNotification({
            type: 'deposit',
            title: language === 'ar' ? `إيداع جديد: ${tx.amount_syp} ل.س` : `New Deposit: ${tx.amount_syp} SYP`,
            body: language === 'ar' ? `من: ${tx.username || 'مستخدم'} - ${tx.wallet_name || ''}` : `From: ${tx.username || 'user'} - ${tx.wallet_name || ''}`,
            data: { tx_id: tx.id, telegram_id: tx.telegram_id }
          });
          // 🔥 نقطة حمراء في السايدبار
          setNewDepositsCount(prev => prev + 1);
        }
      ).subscribe();

    const withdrawalsChannel = supabase.channel('withdrawals_notifications')
      .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'transactions', filter: "type=eq.withdrawal" },
        async payload => {
          const tx = payload.new;
          console.log('[Realtime] New withdrawal:', tx);
          // إشعار في الهيدر
          await addNotification({
            type: 'withdrawal',
            title: language === 'ar' ? `سحب جديد: ${tx.amount_syp} ل.س` : `New Withdrawal: ${tx.amount_syp} SYP`,
            body: language === 'ar' ? `من: ${tx.username || 'مستخدم'} - ${tx.method || ''}` : `From: ${tx.username || 'user'} - ${tx.method || ''}`,
            data: { tx_id: tx.id, telegram_id: tx.telegram_id }
          });
          // 🔥 نقطة حمراء في السايدبار
          setNewWithdrawalsCount(prev => prev + 1);
        }
      ).subscribe();

    const messagesChannel = supabase.channel('messages_notifications')
      .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'messages' },
        async payload => {
          const msg = payload.new;
          console.log('[Realtime] New message:', msg);
          if (msg.direction === 'incoming') {
            // 🔥 نقطة حمراء في السايدبار فقط (بدون إشعار في الهيدر)
            setNewMessagesCount(prev => prev + 1);
          }
        }
      ).subscribe();

    return () => {
      depositsChannel.unsubscribe();
      withdrawalsChannel.unsubscribe();
      messagesChannel.unsubscribe();
    };
  }, [isAuthenticated, language]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.setAttribute('dir', language === 'ar' ? 'rtl' : 'ltr');
    document.documentElement.lang = language;

    localStorage.setItem('theme', theme);
    localStorage.setItem('language', language);
  }, [theme, language]);

  useEffect(() => {
    if (window.Notification.permission === 'default') {
      window.Notification.requestPermission();
    }
  }, []);

  const setTheme = useCallback(async (t: Theme) => {
    setThemeState(t);
    await supabase.from('app_settings').upsert({ key: 'theme', value: t }, { onConflict: 'key' });
  }, []);

  const setLanguage = useCallback(async (l: Language) => {
    setLanguageState(l);
    await supabase.from('app_settings').upsert({ key: 'language', value: l }, { onConflict: 'key' });
  }, []);

  const setExchangeRate = useCallback(async (r: number) => {
    setExchangeRateState(r);
    await supabase.from('app_settings').upsert({ key: 'exchange_rate', value: String(r) }, { onConflict: 'key' });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    if (isLockedOut) {
      return {
        error: language === 'ar'
          ? 'تم تجاوز الحد الأقصى لمحاولات تسجيل الدخول. يرجى الانتظار 15 دقيقة.'
          : 'Too many login attempts. Please wait 15 minutes.'
      };
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      const attempts = loginAttempts + 1;
      setLoginAttempts(attempts);
      localStorage.setItem('loginAttempts', String(attempts));

      if (attempts >= MAX_LOGIN_ATTEMPTS) {
        const lockTime = Date.now();
        setLockoutTime(lockTime);
        localStorage.setItem('lockoutTime', String(lockTime));
      }

      return { error: error.message };
    }

    const user = data?.user;

    // ==============================
    // 🔥 AUTO CREATE USER IN users
    // ==============================
    if (user) {
      const { data: existingUser } = await supabase
        .from('users')
        .select('id')
        .eq('id', user.id)
        .maybeSingle();

      if (!existingUser) {
        await supabase.from('users').insert({
          id: user.id,
          telegram_id: null,
          username: user.email?.split('@')[0] || null,
          first_name: null,
          balance_syp: 0,
          balance_usd: 0,
          is_blocked: false,
          operations_count: 0,
          total_deposits: 0,
          created_at: new Date().toISOString(),
        });
      }
    }
    // ==============================

    const { data: profile, error: profileError } = await supabase
      .from('users')
      .select('role')
      .eq('id', user?.id)
      .maybeSingle();

    if (profileError) {
      console.error("Profile fetch error:", profileError);
      return { error: 'Error fetching user profile' };
    }

    if (!profile) {
      return { error: 'User profile not found' };
    }

    if (profile.role !== 'admin') {
      await supabase.auth.signOut();
      return { error: 'Not authorized (Admin only)' };
    }

    setLoginAttempts(0);
    setLockoutTime(0);
    localStorage.removeItem('loginAttempts');
    localStorage.removeItem('lockoutTime');

    return { error: null };
  }, [isLockedOut, loginAttempts, language]);

  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setIsAuthenticated(false);
    setCurrentPage('dashboard');
  }, []);

  const markAllRead = useCallback(async () => {
    await supabase.from('notifications').update({ is_read: true }).eq('is_read', false);
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  }, []);

  const markRead = useCallback(async (id: string) => {
    await supabase.from('notifications').update({ is_read: true }).eq('id', id);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
  }, []);

  const addNotification = useCallback(async (n: Omit<AppNotification, 'id' | 'created_at' | 'is_read'>) => {
    try {
      const { error } = await supabase.from('notifications').insert({
        ...n,
        is_read: false,
        created_at: new Date().toISOString()
      });
      if (error) console.error('[Notifications] Insert error:', error);
    } catch (err) {
      console.error('[Notifications] Error:', err);
    }
  }, []);

  const unreadCount = notifications.filter(n => !n.is_read && n.type !== 'message').length;  // 🔥 لا نحسب رسائل الهيدر

  // 🔥 دوال مسح النقاط الحمراء
  const clearNewDeposits = useCallback(() => setNewDepositsCount(0), []);
  const clearNewWithdrawals = useCallback(() => setNewWithdrawalsCount(0), []);
  const clearNewMessages = useCallback(() => setNewMessagesCount(0), []);

  return (
    <AppContext.Provider value={{
      theme, setTheme,
      language, setLanguage,
      currentPage, setCurrentPage,
      isAuthenticated, isLoading,
      login, logout,
      notifications, unreadCount,
      markAllRead, markRead, addNotification,
      exchangeRate, setExchangeRate,
      refreshExchangeRate,
      loginAttempts, isLockedOut,
      // 🔥 نقاط حمراء في السايدبار
      newDepositsCount, newWithdrawalsCount, newMessagesCount,
      clearNewDeposits, clearNewWithdrawals, clearNewMessages,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
