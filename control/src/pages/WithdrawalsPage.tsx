import { useState, useEffect, useCallback } from 'react';
import { Search, ChevronLeft, ChevronRight, RefreshCw, TrendingUp, Filter, CheckCircle, XCircle } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useRealtime } from '../hooks/useRealtime';
import type { Transaction } from '../types';

const PAGE_SIZE = 20;

export default function WithdrawalsPage() {
  const { theme, language } = useApp();
  const isDark = theme === 'dark';

  const [txs, setTxs] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'completed' | 'pending' | 'rejected'>('all');
  const [loading, setLoading] = useState(true);
  const [totalSum, setTotalSum] = useState(0);
  const [notificationSettings, setNotificationSettings] = useState<any>({});

  const load = useCallback(async () => {
    console.log('[WithdrawalsPage] Loading transactions...');
    setLoading(true);
    try {
      let q = supabase.from('transactions').select('*', { count: 'exact' }).in('type', ['withdrawal', 'admin_withdraw']);
      if (search) q = q.or(`username.ilike.%${search}%`);
      if (fromDate) q = q.gte('created_at', fromDate);
      if (toDate) q = q.lte('created_at', toDate + 'T23:59:59');
      if (statusFilter !== 'all') q = q.eq('status', statusFilter);
      q = q.order('created_at', { ascending: false }).range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);
      const { data, count, error } = await q;
      if (error) {
        console.error('[WithdrawalsPage] Error loading transactions:', error);
      } else {
        console.log(`[WithdrawalsPage] Loaded ${data?.length || 0} transactions, total: ${count || 0}`);
        console.log('[WithdrawalsPage] Transactions data:', data);
      }
      setTxs(data as Transaction[] || []);
      setTotal(count || 0);

      const { data: sumData } = await supabase.from('transactions').select('amount_syp').in('type', ['withdrawal', 'admin_withdraw']).eq('status', 'completed');
      setTotalSum((sumData || []).reduce((s, r) => s + Number(r.amount_syp), 0));

      // Load notification settings
      const { data: notifData } = await supabase.from('app_settings').select('key, value').in('key', ['withdrawal_approved_message', 'withdrawal_rejected_message']);
      const notifMap: any = {};
      notifData?.forEach(n => notifMap[n.key] = n.value);
      setNotificationSettings(notifMap);
    } finally { setLoading(false) }
  }, [search, fromDate, toDate, statusFilter, page]);

  useEffect(() => { load(); }, [load]);
  useRealtime({ table: 'transactions', onInsert: (payload) => {
    console.log('[WithdrawalsPage] Realtime INSERT received:', payload);
    load();
  } });

  const fmt = (n: number) => new Intl.NumberFormat().format(Math.round(n));
  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Approve withdrawal
  const approveWithdrawal = async (tx: Transaction) => {
    if (!confirm('هل أنت متأكد من الموافقة على هذا السحب؟')) return;

    try {
      // 1. Update transaction status
      const { error: updateError } = await supabase
        .from('transactions')
        .update({ status: 'completed', updated_at: new Date().toISOString() })
        .eq('id', tx.id);

      if (updateError) throw updateError;

      // 2. Get user current balance
      const { data: userData } = await supabase
        .from('users')
        .select('balance_syp')
        .eq('telegram_id', tx.telegram_id)
        .single();

      const currentBalance = userData?.balance_syp || 0;
      const newBalance = Math.max(0, currentBalance - tx.amount_syp);

      // 3. Update user balance (deduct the amount)
      const { error: balanceError } = await supabase
        .from('users')
        .update({ balance_syp: newBalance })
        .eq('telegram_id', tx.telegram_id);

      if (balanceError) throw balanceError;

      // 4. Send notification
      const fee_percentage = tx.fee_amount ? ((tx.fee_amount / tx.amount_syp) * 100).toFixed(2) : '0';
      const net_amount = tx.amount_syp - (tx.fee_amount || 0);

      let message = notificationSettings['withdrawal_approved_message'] ||
        `✅ تمت الموافقة على طلب سحبك!\n\n💰 المبلغ: ${tx.amount_syp.toLocaleString()} ل.س\n✅ المبلغ الصافي: ${net_amount.toLocaleString()} ل.س\n📋 رقم العملية: ${tx.operation_number}`;

      // Replace placeholders
      message = message
        .replace('{amount_syp}', tx.amount_syp.toLocaleString())
        .replace('{fee_percentage}', fee_percentage)
        .replace('{net_amount}', net_amount.toLocaleString())
        .replace('{method_name}', tx.method || '—')
        .replace('{operation_number}', tx.operation_number || '—');

      await supabase.from('pending_notifications').insert({
        telegram_id: tx.telegram_id,
        message: message,
        status: 'pending',
        created_at: new Date().toISOString()
      });

      await load();
      alert('✅ تمت الموافقة على السحب وإرسال الإشعار');
    } catch (error: any) {
      alert('❌ خطأ: ' + error.message);
    }
  };

  // Reject withdrawal
  const rejectWithdrawal = async (tx: Transaction) => {
    if (!confirm('هل أنت متأكد من رفض هذا السحب؟')) return;

    try {
      // 1. Update transaction status
      const { error: updateError } = await supabase
        .from('transactions')
        .update({ status: 'rejected', updated_at: new Date().toISOString() })
        .eq('id', tx.id);

      if (updateError) throw updateError;

      // 2. Send notification
      let message = notificationSettings['withdrawal_rejected_message'] ||
        `❌ تم رفض طلب سحبك\n\n💰 المبلغ: ${tx.amount_syp.toLocaleString()} ل.س\n📋 رقم العملية: ${tx.operation_number}\n\nيرجى التواصل مع الدعم.`;

      // Replace placeholders
      message = message
        .replace('{amount_syp}', tx.amount_syp.toLocaleString())
        .replace('{method_name}', tx.method || '—')
        .replace('{operation_number}', tx.operation_number || '—');

      await supabase.from('pending_notifications').insert({
        telegram_id: tx.telegram_id,
        message: message,
        status: 'pending',
        created_at: new Date().toISOString()
      });

      await load();
      alert('✅ تم رفض السحب وإرسال الإشعار');
    } catch (error: any) {
      alert('❌ خطأ: ' + error.message);
    }
  };

  const inputCls = `px-3 py-2 rounded-xl text-sm border outline-none transition-colors
    ${isDark ? 'bg-slate-800 border-slate-600 text-white placeholder-slate-500 focus:border-blue-500' : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-blue-500'}`;

  return (
    <div className="space-y-4">
      <div className={`rounded-2xl p-4 border flex flex-wrap gap-4 items-center ${isDark ? 'bg-red-500/5 border-red-500/20' : 'bg-red-50 border-red-100'}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-500/15 flex items-center justify-center">
            <TrendingUp size={20} className="text-red-400" />
          </div>
          <div>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{language === 'ar' ? 'إجمالي السحوبات' : 'Total Withdrawals'}</p>
            <p className="text-xl font-bold text-red-400">{fmt(totalSum)} {t(language, 'syp')}</p>
          </div>
        </div>
        <div className={`ms-auto text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{total} {language === 'ar' ? 'عملية' : 'operations'}</div>
      </div>

      <div className={`rounded-2xl border p-4 ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-40">
            <Search size={14} className={`absolute top-1/2 -translate-y-1/2 ${language === 'ar' ? 'right-3' : 'left-3'} text-slate-400`} />
            <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
              placeholder={t(language, 'search')} className={`${inputCls} w-full ${language === 'ar' ? 'pr-9' : 'pl-9'}`} />
          </div>
          <input type="date" value={fromDate} onChange={e => { setFromDate(e.target.value); setPage(1); }} className={inputCls} />
          <input type="date" value={toDate} onChange={e => { setToDate(e.target.value); setPage(1); }} className={inputCls} />
          <div className={`flex rounded-xl overflow-hidden border ${isDark ? 'border-slate-600' : 'border-slate-200'}`}>
            {(['all', 'completed', 'pending', 'rejected'] as const).map(s => (
              <button key={s} onClick={() => { setStatusFilter(s); setPage(1); }}
                className={`px-3 py-2 text-xs font-medium transition-colors
                  ${statusFilter === s ? 'bg-blue-600 text-white' : isDark ? 'bg-slate-800 text-slate-400 hover:text-white' : 'bg-white text-slate-500 hover:text-slate-700'}`}>
                {t(language, s === 'completed' ? 'completed' : s === 'pending' ? 'pending' : s === 'rejected' ? 'rejected' : 'all')}
              </button>
            ))}
          </div>
          <button onClick={() => { setSearch(''); setFromDate(''); setToDate(''); setStatusFilter('all'); setPage(1); }}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            <Filter size={12} /> {t(language, 'clearFilter')}
          </button>
          <button onClick={load} className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            <RefreshCw size={12} /> {t(language, 'refresh')}
          </button>
        </div>
      </div>

      <div className={`rounded-2xl border overflow-hidden ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className={`text-xs ${isDark ? 'bg-slate-900/50 text-slate-400' : 'bg-slate-50 text-slate-500'}`}>
                {['#', t(language, 'username'), t(language, 'type'), t(language, 'amountSYP'), t(language, 'status'), 'الحساب', t(language, 'date'), 'الإجراءات'].map(h => (
                  <th key={h} className="px-4 py-3 text-start font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-slate-700/30' : 'divide-slate-100'}`}>
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>{Array.from({ length: 8 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className={`h-4 rounded animate-pulse ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} style={{ width: `${40 + Math.random() * 40}%` }} />
                    </td>
                  ))}</tr>
                ))
              ) : txs.length === 0 ? (
                <tr><td colSpan={8} className={`px-4 py-10 text-center text-sm ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{t(language, 'noData')}</td></tr>
              ) : txs.map(tx => (
                <tr key={tx.id} className={`transition-colors ${isDark ? 'hover:bg-slate-700/20' : 'hover:bg-slate-50'}`}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{tx.operation_number}</td>
                  <td className={`px-4 py-3 font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>@{tx.username || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium
                      ${tx.type === 'withdrawal' ? 'bg-red-500/15 text-red-400' : 'bg-amber-500/15 text-amber-400'}`}>
                      {t(language, tx.type === 'withdrawal' ? 'withdrawal' : 'adminWithdraw')}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-medium text-red-400">-{fmt(tx.amount_syp)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium
                      ${tx.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400'
                      : tx.status === 'pending' ? 'bg-amber-500/15 text-amber-400'
                      : 'bg-red-500/15 text-red-400'}`}>
                      {t(language, tx.status === 'completed' ? 'completed' : tx.status === 'pending' ? 'pending' : 'rejected')}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{tx.account_number || '—'}</td>
                  <td className={`px-4 py-3 text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {new Date(tx.created_at).toLocaleString(language === 'ar' ? 'ar-SA' : 'en-US', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td className="px-4 py-3">
                    {tx.status === 'pending' && (
                      <div className="flex gap-1">
                        <button
                          onClick={() => approveWithdrawal(tx)}
                          className="p-1.5 rounded-lg bg-emerald-100 text-emerald-600 hover:bg-emerald-200"
                          title="موافقة"
                        >
                          <CheckCircle size={16} />
                        </button>
                        <button
                          onClick={() => rejectWithdrawal(tx)}
                          className="p-1.5 rounded-lg bg-red-100 text-red-600 hover:bg-red-200"
                          title="رفض"
                        >
                          <XCircle size={16} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={`flex items-center justify-between px-4 py-3 border-t text-xs ${isDark ? 'border-slate-700/40 text-slate-400' : 'border-slate-100 text-slate-500'}`}>
          <span>{language === 'ar' ? `${total} عملية — صفحة ${page} من ${totalPages || 1}` : `${total} operations — Page ${page} of ${totalPages || 1}`}</span>
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
