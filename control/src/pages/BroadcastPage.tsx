import { useState, useEffect, useCallback } from 'react';
import { Send, Users, CheckCircle, AlertCircle, RefreshCw, MessageSquare } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { useRealtime } from '../hooks/useRealtime';

type Broadcast = {
  id: string;
  message: string;
  sent_count: number;
  failed_count: number;
  status: 'pending' | 'sending' | 'completed';
  created_at: string;
  completed_at?: string;
};

export default function BroadcastPage() {
  const { theme, language, isAuthenticated } = useApp();
  const isDark = theme === 'dark';

  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [userCount, setUserCount] = useState(0);

  const loadBroadcasts = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      const { data } = await supabase
        .from('broadcast_messages')
        .select('*')
        .order('created_at', { ascending: false });
      setBroadcasts(data || []);
      
      // Get user count
      const { count } = await supabase.from('users').select('*', { count: 'exact', head: true });
      setUserCount(count || 0);
    } catch (e) {
      console.error('Error:', e);
    }
    setLoading(false);
  }, [isAuthenticated]);

  useEffect(() => { loadBroadcasts(); }, [loadBroadcasts]);
  useRealtime({ table: 'broadcast_messages', onInsert: loadBroadcasts, onUpdate: loadBroadcasts });

  const sendBroadcast = async () => {
    if (!message.trim()) {
      alert(language === 'ar' ? 'يرجى إدخال رسالة' : 'Please enter a message');
      return;
    }
    if (!confirm(language === 'ar' ? `إرسال لـ ${userCount} مستخدم؟` : `Send to ${userCount} users?`)) return;

    setSending(true);
    try {
      // Insert broadcast record
      const { data: broadcast } = await supabase.from('broadcast_messages').insert({
        message: message.trim(),
        status: 'pending'
      }).select().single();

      // Get all users
      const { data: users } = await supabase.from('users').select('telegram_id');
      if (!users || users.length === 0) {
        alert(language === 'ar' ? 'لا يوجد مستخدمين' : 'No users found');
        return;
      }

      // Queue notifications
      const notifications = users.map(u => ({
        telegram_id: u.telegram_id,
        message: `📢 رسالة من الإدارة:\n\n${message.trim()}`,
        status: 'pending',
        broadcast_id: broadcast.id
      }));

      // Insert in batches
      const batchSize = 100;
      for (let i = 0; i < notifications.length; i += batchSize) {
        const batch = notifications.slice(i, i + batchSize);
        await supabase.from('pending_notifications').insert(batch);
      }

      // Update broadcast
      await supabase.from('broadcast_messages').update({
        status: 'completed',
        sent_count: users.length,
        completed_at: new Date().toISOString()
      }).eq('id', broadcast.id);

      setMessage('');
      alert(language === 'ar' ? 'تم إرسال الرسالة بنجاح' : 'Message sent successfully');
      loadBroadcasts();
    } catch (e) {
      console.error('Error:', e);
      alert(language === 'ar' ? 'فشل في الإرسال' : 'Failed to send');
    }
    setSending(false);
  };

  const card = `rounded-2xl border p-4 ${isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}`;
  const input = `w-full px-3 py-2 rounded-xl text-sm border outline-none ${isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'}`;

  return (
    <div className="space-y-4">
      {/* STATS */}
      <div className={card}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/15 flex items-center justify-center">
            <Users size={20} className="text-blue-400" />
          </div>
          <div>
            <p className="text-xs opacity-70">{language === 'ar' ? 'إجمالي المستخدمين' : 'Total Users'}</p>
            <p className="text-xl font-bold">{userCount.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* SEND FORM */}
      <div className={card}>
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare size={18} />
          <h2 className="font-semibold">{language === 'ar' ? 'إرسال رسالة جماعية' : 'Send Broadcast'}</h2>
        </div>

        <textarea
          className={`${input} min-h-[120px] resize-none`}
          placeholder={language === 'ar' ? 'اكتب رسالتك هنا...' : 'Type your message here...'}
          value={message}
          onChange={e => setMessage(e.target.value)}
        />

        <div className="flex justify-between items-center mt-3">
          <span className="text-xs opacity-70">
            {language === 'ar' ? `سيتم الإرسال لـ ${userCount} مستخدم` : `Will be sent to ${userCount} users`}
          </span>
          <button
            onClick={sendBroadcast}
            disabled={sending || !message.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl disabled:opacity-50"
          >
            {sending ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />}
            {language === 'ar' ? 'إرسال' : 'Send'}
          </button>
        </div>
      </div>

      {/* HISTORY */}
      <div className={card}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">{language === 'ar' ? 'سجل الرسائل' : 'Message History'}</h3>
          <button onClick={loadBroadcasts} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        <div className="space-y-2">
          {broadcasts.map(b => (
            <div key={b.id} className={`p-3 rounded-xl ${isDark ? 'bg-slate-700/50' : 'bg-slate-50'}`}>
              <p className="text-sm mb-2 whitespace-pre-wrap">{b.message}</p>
              <div className="flex items-center gap-4 text-xs opacity-70">
                <span className="flex items-center gap-1">
                  {b.status === 'completed' ? <CheckCircle size={12} className="text-green-500" /> : <AlertCircle size={12} />}
                  {b.sent_count} {language === 'ar' ? 'مستلم' : 'sent'}
                </span>
                <span>{new Date(b.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>

        {broadcasts.length === 0 && (
          <div className="text-center py-8 opacity-50">
            {language === 'ar' ? 'لا توجد رسائل سابقة' : 'No messages yet'}
          </div>
        )}
      </div>
    </div>
  );
}
