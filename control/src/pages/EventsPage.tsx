import { useState, useEffect, useCallback } from 'react';
import { Search, Activity, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useRealtime } from '../hooks/useRealtime';

const PAGE_SIZE = 20;

interface EventItem {
  id: string;
  type: string;
  description: string;
  created_at: string;
}

/* 🔥 تحسين: ألوان حسب النوع */
const getTypeColor = (type: string) => {
  switch (type) {
    case 'error':
      return 'text-red-400 bg-red-500/10';
    case 'success':
      return 'text-green-400 bg-green-500/10';
    case 'warning':
      return 'text-yellow-400 bg-yellow-500/10';
    default:
      return 'text-purple-400 bg-purple-500/10';
  }
};

export default function EventsPage() {
  const { theme, language } = useApp();
  const isDark = theme === 'dark';

  const [events, setEvents] = useState<EventItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      let q = supabase.from('events').select('*', { count: 'exact' });

      if (search) {
        q = q.or(`type.ilike.%${search}%,description.ilike.%${search}%`);
      }

      q = q
        .order('created_at', { ascending: false })
        .range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);

      const { data, count } = await q;

      setEvents((data as EventItem[]) || []);
      setTotal(count || 0);
    } finally {
      setLoading(false);
    }
  }, [search, page]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  /* 🔥 تحسين realtime أقوى */
  useRealtime({
    table: 'events',
    onInsert: (payload) => {
      setEvents(prev => [payload.new as EventItem, ...prev]);
      setTotal(prev => prev + 1);
    },
    onUpdate: loadEvents,
    onDelete: loadEvents,
  });

  /* 🔥 auto refresh */
  useEffect(() => {
    const interval = setInterval(loadEvents, 30000);
    return () => clearInterval(interval);
  }, [loadEvents]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className={`rounded-2xl border p-4 ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-wrap gap-3 items-center">

          <div className="relative flex-1 min-w-48">
            <Search
              size={14}
              className={`absolute top-1/2 -translate-y-1/2 ${language === 'ar' ? 'right-3' : 'left-3'} text-slate-400`}
            />
            <input
              value={search}
              onChange={e => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder={language === 'ar' ? 'بحث...' : 'Search...'}
              className={`w-full px-3 py-2 rounded-xl text-sm border outline-none ${language === 'ar' ? 'pr-9' : 'pl-9'}
                ${isDark
                  ? 'bg-slate-800 border-slate-600 text-white placeholder-slate-500 focus:border-blue-500'
                  : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-blue-500'}`}
            />
          </div>

          <button
            onClick={loadEvents}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors
              ${isDark
                ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            <RefreshCw size={12} />
            {t(language, 'refresh')}
          </button>
        </div>
      </div>

      {/* List */}
      <div className={`rounded-2xl border overflow-hidden ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>

        <div className="divide-y divide-slate-700/20">

          {loading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 px-5 py-4">
                <div className={`w-9 h-9 rounded-full animate-pulse ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} />
                <div className="flex-1 space-y-2">
                  <div className={`h-3 rounded animate-pulse w-32 ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} />
                  <div className={`h-3 rounded animate-pulse w-full ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} />
                </div>
              </div>
            ))
          ) : events.length === 0 ? (
            <div className={`py-16 text-center ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
              <Activity size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">{t(language, 'noData')}</p>
            </div>
          ) : (
            events.map(event => (
              <div
                key={event.id}
                className={`flex items-start gap-3 px-5 py-4 transition-colors
                  ${isDark ? 'hover:bg-slate-700/20' : 'hover:bg-slate-50'}`}
              >

                {/* icon */}
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${getTypeColor(event.type)}`}>
                  <Activity size={16} />
                </div>

                <div className="flex-1 min-w-0">

                  {/* type badge */}
                  <div className="mb-1">
                    <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getTypeColor(event.type)}`}>
                      {event.type || 'event'}
                    </span>
                  </div>

                  <p className={`text-sm break-words ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                    {event.description || '—'}
                  </p>

                  <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {new Date(event.created_at).toLocaleString(
                      language === 'ar' ? 'ar-SA' : 'en-US',
                      { dateStyle: 'medium', timeStyle: 'short' }
                    )}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        <div className={`flex items-center justify-between px-5 py-3 border-t text-xs ${isDark ? 'border-slate-700/40 text-slate-400' : 'border-slate-100 text-slate-500'}`}>
          <span>{language === 'ar' ? `${total} نشاط` : `${total} events`}</span>

          <div className="flex gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className={`p-1.5 rounded-lg ${page === 1
                ? 'opacity-30 cursor-not-allowed'
                : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}
            >
              {language === 'ar' ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            <span className="px-2 py-1">{page}/{totalPages || 1}</span>

            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className={`p-1.5 rounded-lg ${page >= totalPages
                ? 'opacity-30 cursor-not-allowed'
                : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}
            >
              {language === 'ar' ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}