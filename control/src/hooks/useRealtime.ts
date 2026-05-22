import { useEffect, useRef, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { useApp } from '../contexts/GlobalContext';

type RealtimeTable = 'users' | 'transactions' | 'messages' | 'notifications' | 'bot_balance' | 'wallets' | 'app_settings' | 'gift_codes' | 'broadcast_messages' | 'withdrawal_methods' | 'pending_notifications';

interface UseRealtimeOptions {
  table: RealtimeTable;
  onInsert?: (payload: Record<string, unknown>) => void;
  onUpdate?: (payload: Record<string, unknown>) => void;
  onDelete?: (payload: Record<string, unknown>) => void;
}

export function useRealtime({ table, onInsert, onUpdate, onDelete }: UseRealtimeOptions) {
  const { isAuthenticated } = useApp();
  const channelRef = useRef<ReturnType<typeof supabase.channel> | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      console.log(`[Realtime] Not authenticated, skipping subscription for ${table}`);
      return;
    }

    console.log(`[Realtime] Setting up subscription for ${table}`);

    const channel = supabase.channel(`realtime_${table}_${Date.now()}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table }, payload => {
        console.log(`[Realtime] INSERT on ${table}:`, payload);
        onInsert?.(payload.new as Record<string, unknown>);
      })
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table }, payload => {
        console.log(`[Realtime] UPDATE on ${table}:`, payload);
        onUpdate?.(payload.new as Record<string, unknown>);
      })
      .on('postgres_changes', { event: 'DELETE', schema: 'public', table }, payload => {
        console.log(`[Realtime] DELETE on ${table}:`, payload);
        onDelete?.(payload.old as Record<string, unknown>);
      })
      .subscribe((status) => {
        console.log(`[Realtime] Subscription status for ${table}:`, status);
      });

    channelRef.current = channel;
    return () => {
      console.log(`[Realtime] Unsubscribing from ${table}`);
      channel.unsubscribe();
    };
  }, [isAuthenticated, table, onInsert, onUpdate, onDelete]);
}

export function useDashboardRealtime(onAnyChange: () => void) {
  const { isAuthenticated, addNotification, language } = useApp();

  const handleChange = useCallback(() => { onAnyChange(); }, [onAnyChange]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const channel = supabase.channel('dashboard_realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'transactions' }, payload => {
        const tx = payload.new as Record<string, unknown>;
        const isDeposit = tx.type === 'deposit';
        addNotification({
          type: isDeposit ? 'deposit' : 'withdrawal',
          title: language === 'ar' ? (isDeposit ? 'إيداع جديد' : 'سحب جديد') : (isDeposit ? 'New Deposit' : 'New Withdrawal'),
          body: language === 'ar'
            ? `${isDeposit ? 'إيداع' : 'سحب'} بقيمة ${tx.amount_syp} ل.س من @${tx.username}`
            : `${isDeposit ? 'Deposit' : 'Withdrawal'} of ${tx.amount_syp} SYP from @${tx.username}`,
          data: tx,
        });
        handleChange();
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'users' }, payload => {
        const user = payload.new as Record<string, unknown>;
        addNotification({
          type: 'user',
          title: language === 'ar' ? 'مستخدم جديد' : 'New User',
          body: language === 'ar'
            ? `انضم @${user.username || user.telegram_id} إلى البوت`
            : `@${user.username || user.telegram_id} joined the bot`,
          data: user,
        });
        handleChange();
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages' }, payload => {
        const msg = payload.new as Record<string, unknown>;
        if (msg.direction === 'incoming') {
          addNotification({
            type: 'message',
            title: language === 'ar' ? 'رسالة جديدة' : 'New Message',
            body: language === 'ar'
              ? `رسالة من @${msg.username}: ${String(msg.content).substring(0, 50)}`
              : `Message from @${msg.username}: ${String(msg.content).substring(0, 50)}`,
            data: msg,
          });
        }
        handleChange();
      })
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'users' }, () => handleChange())
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'bot_balance' }, () => handleChange())
      .subscribe();

    return () => { channel.unsubscribe(); };
  }, [isAuthenticated, addNotification, language, handleChange]);
}
