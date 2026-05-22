import { useState, useEffect, useCallback } from 'react';
import { Search, ChevronLeft, ChevronRight, RefreshCw, TrendingDown, Filter, Check, X, Loader2 } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useRealtime } from '../hooks/useRealtime';
import type { Transaction } from '../types';

const PAGE_SIZE = 20;

export default function DepositsPage() {
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
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [totalSum, setTotalSum] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      let q = supabase.from('transactions').select('*', { count: 'exact' }).eq('type', 'deposit');
      if (search) q = q.or(`username.ilike.%${search}%,wallet_name.ilike.%${search}%`);
      if (fromDate) q = q.gte('created_at', fromDate);
      if (toDate) q = q.lte('created_at', toDate + 'T23:59:59');
      if (statusFilter !== 'all') q = q.eq('status', statusFilter);
      q = q.order('created_at', { ascending: false }).range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);
      const { data, count } = await q;
      setTxs(data as Transaction[] || []);
      setTotal(count || 0);

      const { data: sumData } = await supabase.from('transactions').select('amount_syp').eq('type', 'deposit').eq('status', 'completed');
      setTotalSum((sumData || []).reduce((s, r) => s + Number(r.amount_syp), 0));
    } finally { setLoading(false); }
  }, [search, fromDate, toDate, statusFilter, page]);

  useEffect(() => { load(); }, [load]);
  useRealtime({ table: 'transactions', onInsert: () => load(), onUpdate: () => load() });

  const approveDeposit = async (id: string, telegram_id: number, amount_syp: number, wallet_name: string, operation_number: number, wallet_key?: string) => {
    // Ask for custom amount
    const customAmount = prompt(
      language === 'ar' 
        ? `المبلغ الأصلي للإيداع: ${amount_syp.toLocaleString()} ل.س\n\nأدخل المبلغ الذي سيتم إضافته إلى رصيد المستخدم (اتركه كما هو للمبلغ الأصلي):`
        : `Original deposit amount: ${amount_syp.toLocaleString()} SYP\n\nEnter the amount to add to user's balance (leave as is for original amount):`,
      amount_syp.toString()
    );
    
    const finalAmount = customAmount ? Number(customAmount) : amount_syp;
    
    if (isNaN(finalAmount) || finalAmount <= 0) {
      alert(language === 'ar' ? 'المبلغ غير صالح' : 'Invalid amount');
      return;
    }

    if (!confirm(language === 'ar' 
      ? `الموافقة على هذا الإيداع؟\nالمبلغ الذي سيتم إضافته: ${finalAmount.toLocaleString()} ل.س`
      : `Approve this deposit?\nAmount to be added: ${finalAmount.toLocaleString()} SYP`)) return;
    
    setProcessingId(id);
    try {
      // Get wallet bonus percentage
      let bonusPercentage = 0;
      if (wallet_name) {
        const { data: wallet } = await supabase.from('wallets').select('bonus_percentage').eq('name', wallet_name).single();
        bonusPercentage = wallet?.bonus_percentage || 0;
      }
      
      // Calculate bonus amount
      const bonusAmount = Math.floor(finalAmount * (bonusPercentage / 100));
      const totalAmount = finalAmount + bonusAmount;

      // Get the approval message template
      const { data: settings } = await supabase.from('app_settings').select('value').eq('key', 'deposit_approved_message').single();
      let message = settings?.value || `✅ تمت الموافقة على إيداعك!\n\n💰 المبلغ الأصلي: {amount_syp} ل.س\n💰 المبلغ المضاف: {finalAmount} ل.س\n🏦 المحفظة: {wallet_name}\n📊 رقم العملية: {operation_number}\n\nتم إضافة المبلغ إلى رصيدك.`;
      
      // Replace placeholders
      message = message
        .replace('{amount_syp}', amount_syp.toLocaleString())
        .replace('{final_amount}', finalAmount.toLocaleString())
        .replace('{wallet_name}', wallet_name || '')
        .replace('{operation_number}', operation_number?.toString() || '');

      // Add bonus info if applicable
      if (bonusAmount > 0) {
        message += `\n\n🎁 بونص إضافي: ${bonusAmount.toLocaleString()} ل.س (${bonusPercentage}%)`;
      }

      // Update transaction status and bonus info
      const { error: txError } = await supabase.from('transactions').update({ 
        status: 'completed',
        bonus_amount: bonusAmount,
        bonus_percentage: bonusPercentage,
        total_amount: totalAmount
      }).eq('id', id);
      if (txError) throw txError;

      // Update user balance and get new balance
      const { data: user } = await supabase.from('users').select('id, balance_syp').eq('telegram_id', telegram_id).single();
      let newBalance = 0;
      if (user) {
        newBalance = (user.balance_syp || 0) + totalAmount;
        await supabase.from('users').update({ balance_syp: newBalance }).eq('id', user.id);
      }

      // Add balance info to message
      message += `\n\n💳 رصيدك الجديد: ${newBalance.toLocaleString()} ل.س`;
      if (bonusAmount > 0) {
        message += `\n✨ الإجمالي بعد البونص: ${totalAmount.toLocaleString()} ل.س`;
      }
      
      // Add info about original vs final amount if different
      if (finalAmount !== amount_syp) {
        message += `\n\n📝 ملاحظة: المبلغ الأصلي للإيداع: ${amount_syp.toLocaleString()} ل.س`;
        message += `\n💰 المبلغ المضاف إلى الرصيد: ${finalAmount.toLocaleString()} ل.س`;
      }

      // Add notification to queue
      await supabase.from('pending_notifications').insert({
        telegram_id,
        message,
        status: 'pending'
      });

      load();
    } catch (e: any) {
      console.error('Approve error:', e);
      const errorMsg = e?.message || e?.error?.message || JSON.stringify(e);
      alert(language === 'ar' ? `فشل في الموافقة: ${errorMsg}` : `Failed to approve: ${errorMsg}`);
    } finally {
      setProcessingId(null);
    }
  };

  const rejectDeposit = async (id: string, telegram_id: number, amount_syp: number, wallet_name: string, operation_number: number) => {
    if (!confirm(language === 'ar' ? 'رفض هذا الإيداع؟' : 'Reject this deposit?')) return;
    setProcessingId(id);
    try {
      // Get the rejection message template
      const { data: settings } = await supabase.from('app_settings').select('value').eq('key', 'deposit_rejected_message').single();
      let message = settings?.value || '❌ تم رفض إيداعك\n\n💰 المبلغ: {amount_syp} ل.س\n🏦 المحفظة: {wallet_name}\n📊 رقم العملية: {operation_number}\n\nيرجى التواصل مع الدعم للمزيد من المعلومات.';
      
      // Replace placeholders
      message = message
        .replace('{amount_syp}', amount_syp.toLocaleString())
        .replace('{wallet_name}', wallet_name || '')
        .replace('{operation_number}', operation_number?.toString() || '');

      // Add notification to queue
      await supabase.from('pending_notifications').insert({
        telegram_id,
        message,
        status: 'pending'
      });

      const { error } = await supabase.from('transactions').update({ status: 'rejected' }).eq('id', id);
      if (error) throw error;
      load();
    } catch (e) {
      console.error('Reject error:', e);
      alert(language === 'ar' ? 'فشل في الرفض' : 'Failed to reject');
    } finally {
      setProcessingId(null);
    }
  };

  const fmt = (n: number) => new Intl.NumberFormat().format(Math.round(n));
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const inputCls = `px-3 py-2 rounded-xl text-sm border outline-none transition-colors
    ${isDark ? 'bg-slate-800 border-slate-600 text-white placeholder-slate-500 focus:border-blue-500' : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-blue-500'}`;

  return (
    <div className="space-y-4">
      <div className={`rounded-2xl p-4 border flex flex-wrap gap-4 items-center ${isDark ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-emerald-50 border-emerald-100'}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center">
            <TrendingDown size={20} className="text-emerald-400" />
          </div>
          <div>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{language === 'ar' ? 'إجمالي الإيداعات' : 'Total Deposits'}</p>
            <p className={`text-xl font-bold text-emerald-400`}>{fmt(totalSum)} {t(language, 'syp')}</p>
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
          <input type="date" value={fromDate} onChange={e => { setFromDate(e.target.value); setPage(1); }}
            className={`${inputCls}`} />
          <input type="date" value={toDate} onChange={e => { setToDate(e.target.value); setPage(1); }}
            className={`${inputCls}`} />
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
                {['#', t(language, 'username'), t(language, 'walletName'), t(language, 'amountSYP'), t(language, 'amountUSD'), t(language, 'exchangeRate'), t(language, 'status'), t(language, 'date'), t(language, 'actions')].map(h => (
                  <th key={h} className="px-4 py-3 text-start font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-slate-700/30' : 'divide-slate-100'}`}>
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className={`h-4 rounded animate-pulse ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} style={{ width: `${40 + Math.random() * 40}%` }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : txs.length === 0 ? (
                <tr><td colSpan={8} className={`px-4 py-10 text-center text-sm ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{t(language, 'noData')}</td></tr>
              ) : txs.map(tx => (
                <tr key={tx.id} className={`transition-colors ${isDark ? 'hover:bg-slate-700/20' : 'hover:bg-slate-50'}`}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{tx.operation_number}</td>
                  <td className={`px-4 py-3 font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>@{tx.username || '—'}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{tx.wallet_name || '—'}</td>
                  <td className="px-4 py-3 font-medium text-emerald-400">+{fmt(tx.amount_syp)}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>${Number(tx.amount_usd).toFixed(2)}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{fmt(tx.exchange_rate)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium
                      ${tx.status === 'completed' ? 'bg-emerald-500/15 text-emerald-400'
                      : tx.status === 'pending' ? 'bg-amber-500/15 text-amber-400'
                      : 'bg-red-500/15 text-red-400'}`}>
                      {t(language, tx.status === 'completed' ? 'completed' : tx.status === 'pending' ? 'pending' : 'rejected')}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {new Date(tx.created_at).toLocaleString(language === 'ar' ? 'ar-SA' : 'en-US', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td className="px-4 py-3">
                    {tx.status === 'pending' && (
                      <div className="flex gap-1">
                        <button
                          onClick={() => approveDeposit(tx.id, tx.telegram_id, tx.amount_syp, tx.wallet_name, tx.operation_number)}
                          disabled={processingId === tx.id}
                          className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
                          title={language === 'ar' ? 'موافقة' : 'Approve'}
                        >
                          {processingId === tx.id ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                        </button>
                        <button
                          onClick={() => rejectDeposit(tx.id, tx.telegram_id, tx.amount_syp, tx.wallet_name, tx.operation_number)}
                          disabled={processingId === tx.id}
                          className="p-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
                          title={language === 'ar' ? 'رفض' : 'Reject'}
                        >
                          <X size={14} />
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
