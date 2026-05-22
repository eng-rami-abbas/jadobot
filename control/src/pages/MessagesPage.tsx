import { useState, useEffect, useCallback } from 'react';
import { Search, MessageCircle, ChevronLeft, ChevronRight, RefreshCw, CheckCheck } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useRealtime } from '../hooks/useRealtime';
import type { Message } from '../types';

const PAGE_SIZE = 20;

export default function MessagesPage() {
  const { theme, language } = useApp();
  const isDark = theme === 'dark';

  const [messages, setMessages] = useState<Message[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filterDir, setFilterDir] = useState<'all' | 'incoming' | 'outgoing'>('all');
  const [loading, setLoading] = useState(true);


  const loadMessages = useCallback(async () => {
    setLoading(true);
    try {
      let q = supabase.from('messages').select('*', { count: 'exact' });
      if (search) q = q.or(`username.ilike.%${search}%,content.ilike.%${search}%`);
      if (filterDir !== 'all') q = q.eq('direction', filterDir);
      q = q.order('created_at', { ascending: false }).range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);
      const { data, count } = await q;
      setMessages(data as Message[] || []);
      setTotal(count || 0);
    } finally { setLoading(false); }
  }, [search, filterDir, page]);

  useEffect(() => { loadMessages(); }, [loadMessages]);
  useRealtime({ table: 'messages', onInsert: () => loadMessages() });

  const markAllRead = async () => {
    await supabase.from('messages').update({ is_read: true }).eq('is_read', false).eq('direction', 'incoming');
    loadMessages();
  };

  const unread = messages.filter(m => !m.is_read && m.direction === 'incoming').length;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      <div className={`rounded-2xl border p-4 ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-48">
            <Search size={14} className={`absolute top-1/2 -translate-y-1/2 ${language === 'ar' ? 'right-3' : 'left-3'} ${isDark ? 'text-slate-400' : 'text-slate-400'}`} />
            <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
              placeholder={t(language, 'search')}
              className={`w-full px-3 py-2 rounded-xl text-sm border outline-none ${language === 'ar' ? 'pr-9' : 'pl-9'}
                ${isDark ? 'bg-slate-800 border-slate-600 text-white placeholder-slate-500 focus:border-blue-500' : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-blue-500'}`} />
          </div>
          <div className={`flex rounded-xl overflow-hidden border ${isDark ? 'border-slate-600' : 'border-slate-200'}`}>
            {(['all', 'incoming', 'outgoing'] as const).map(d => (
              <button key={d} onClick={() => { setFilterDir(d); setPage(1); }}
                className={`px-3 py-2 text-xs font-medium transition-colors
                  ${filterDir === d ? 'bg-blue-600 text-white' : isDark ? 'bg-slate-800 text-slate-400 hover:text-white' : 'bg-white text-slate-500 hover:text-slate-700'}`}>
                {t(language, d === 'incoming' ? 'incoming' : d === 'outgoing' ? 'outgoing' : 'all')}
              </button>
            ))}
          </div>
          {unread > 0 && (
            <button onClick={markAllRead} className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors
              ${isDark ? 'bg-blue-600/20 text-blue-400 hover:bg-blue-600/30' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'}`}>
              <CheckCheck size={12} /> {t(language, 'markAllRead')} ({unread})
            </button>
          )}
          <button onClick={loadMessages} className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors
            ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            <RefreshCw size={12} /> {t(language, 'refresh')}
          </button>
        </div>
      </div>

      <div className={`rounded-2xl border overflow-hidden ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="divide-y divide-slate-700/20">
          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={`flex items-start gap-3 px-5 py-4`}>
                <div className={`w-9 h-9 rounded-full animate-pulse ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} />
                <div className="flex-1 space-y-2">
                  <div className={`h-3 rounded animate-pulse w-32 ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} />
                  <div className={`h-3 rounded animate-pulse w-full ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} />
                </div>
              </div>
            ))
          ) : messages.length === 0 ? (
            <div className={`py-16 text-center ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
              <MessageCircle size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">{t(language, 'noData')}</p>
            </div>
          ) : messages.map(msg => (
            <div key={msg.id}
              className={`flex items-start gap-3 px-5 py-4 transition-colors
                ${!msg.is_read && msg.direction === 'incoming' ? (isDark ? 'bg-blue-500/5' : 'bg-blue-50/50') : ''}
                ${isDark ? 'hover:bg-slate-700/20' : 'hover:bg-slate-50'}`}>
              <div className={`w-9 h-9 rounded-xl flex-shrink-0 flex items-center justify-center text-sm font-bold
                ${msg.direction === 'incoming' ? 'bg-blue-500/15 text-blue-400' : 'bg-emerald-500/15 text-emerald-400'}`}>
                {msg.direction === 'incoming' ? '↓' : '↑'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-sm font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>
                    @{msg.username || msg.telegram_id || '—'}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium
                    ${msg.direction === 'incoming' ? 'bg-blue-500/15 text-blue-400' : 'bg-emerald-500/15 text-emerald-400'}`}>
                    {t(language, msg.direction === 'incoming' ? 'incoming' : 'outgoing')}
                  </span>
                  {!msg.is_read && msg.direction === 'incoming' && (
                    <span className="w-2 h-2 rounded-full bg-blue-500" />
                  )}
                </div>
                <p className={`text-sm break-words ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{msg.content}</p>
                <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                  {new Date(msg.created_at).toLocaleString(language === 'ar' ? 'ar-SA' : 'en-US', { dateStyle: 'medium', timeStyle: 'short' })}
                </p>
              </div>
            </div>
          ))}
        </div>
        <div className={`flex items-center justify-between px-5 py-3 border-t text-xs ${isDark ? 'border-slate-700/40 text-slate-400' : 'border-slate-100 text-slate-500'}`}>
          <span>{language === 'ar' ? `${total} رسالة` : `${total} messages`}</span>
          <div className="flex gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className={`p-1.5 rounded-lg ${page === 1 ? 'opacity-30 cursor-not-allowed' : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}>
              {language === 'ar' ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
            <span className="px-2 py-1">{page}/{totalPages || 1}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              className={`p-1.5 rounded-lg ${page >= totalPages ? 'opacity-30 cursor-not-allowed' : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}>
              {language === 'ar' ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
