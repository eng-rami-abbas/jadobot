import { useState, useEffect, useCallback } from 'react';
import { Search, Ban, Gift, ArrowUpFromLine, Lock, ChevronLeft, ChevronRight, RefreshCw, Eye, CheckCircle, XCircle } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useRealtime } from '../hooks/useRealtime';
import Modal from '../components/ui/Modal';
import type { BotUser, Transaction } from '../types';

const PAGE_SIZE = 15;

export default function UsersPage() {
  const { theme, language, exchangeRate } = useApp();
  const isDark = theme === 'dark';

  const [users, setUsers] = useState<BotUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'blocked'>('all');
  const [loading, setLoading] = useState(true);

  const [selectedUser, setSelectedUser] = useState<BotUser | null>(null);
  const [userTxs, setUserTxs] = useState<Transaction[]>([]);
  const [txPage, setTxPage] = useState(1);
  const [txTotal, setTxTotal] = useState(0);
  const [modalMode, setModalMode] = useState<'view' | 'gift' | 'withdraw' | 'block' | 'delete' | 'changePassword' | null>(null);
  const [amount, setAmount] = useState('');
  const [amountType, setAmountType] = useState<'syp' | 'usd'>('syp');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      let q = supabase.from('users').select('*', { count: 'exact' });

      // ✅ FIX: تحسين الفلترة
      if (search) {
        const searchValue = search.trim();
        q = q.or(
          `username.ilike.%${searchValue}%,first_name.ilike.%${searchValue}%${
            !isNaN(Number(searchValue)) ? `,telegram_id.eq.${searchValue}` : ''
          }`
        );
      }

      if (filterStatus === 'active') q = q.eq('is_blocked', false);
      if (filterStatus === 'blocked') q = q.eq('is_blocked', true);

      q = q
        .order('created_at', { ascending: false })
        .range((page - 1) * PAGE_SIZE, page * PAGE_SIZE - 1);

      // ✅ FIX: إضافة error handling
      const { data, count, error } = await q;

      if (error) {
        console.error("Users fetch error:", error.message);
        setUsers([]);
        setTotal(0);
        return;
      }

      setUsers(data as BotUser[] || []);
      setTotal(count || 0);

    } catch (err) {
      console.error("Unexpected error:", err);
      setUsers([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [search, filterStatus, page]);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  useRealtime({
    table: 'users',
    onInsert: () => loadUsers(),
    onUpdate: () => loadUsers()
  });

  const loadUserTxs = useCallback(async (userId: string) => {
    const TX_SIZE = 10;

    const { data, count, error } = await supabase
      .from('transactions')
      .select('*', { count: 'exact' })
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .range((txPage - 1) * TX_SIZE, txPage * TX_SIZE - 1);

    if (error) {
      console.error("Transactions error:", error.message);
      setUserTxs([]);
      setTxTotal(0);
      return;
    }

    setUserTxs(data as Transaction[] || []);
    setTxTotal(count || 0);
  }, [txPage]);

  useEffect(() => {
    if (selectedUser && modalMode === 'view') loadUserTxs(selectedUser.id);
  }, [selectedUser, modalMode, loadUserTxs]);

  const openModal = (user: BotUser, mode: typeof modalMode) => {
    setSelectedUser(user);
    setModalMode(mode);
    setAmount('');
    setActionMsg(null);
    setTxPage(1);
  };

  const closeModal = () => {
    setSelectedUser(null);
    setModalMode(null);
    setActionMsg(null);
  };

  const handleGift = async () => {
    if (!selectedUser || !amount) return;
    setActionLoading(true);
    try {
      const amtSYP = amountType === 'usd' ? Number(amount) * exchangeRate : Number(amount);
      const amtUSD = amountType === 'usd' ? Number(amount) : Number(amount) / exchangeRate;

      const { error: e1 } = await supabase.from('users').update({
        balance_syp: selectedUser.balance_syp + amtSYP,
        balance_usd: selectedUser.balance_usd + amtUSD,
        operations_count: selectedUser.operations_count + 1,
      }).eq('id', selectedUser.id);

      if (e1) throw e1;

      const { data: bal } = await supabase.from('bot_balance').select('*').maybeSingle();
      if (bal) {
        await supabase.from('bot_balance').update({
          balance_syp: Math.max(0, bal.balance_syp - amtSYP),
          balance_usd: Math.max(0, bal.balance_usd - amtUSD),
          updated_at: new Date().toISOString(),
        }).eq('id', bal.id);
      }

      await supabase.from('transactions').insert({
        user_id: selectedUser.id,
        telegram_id: selectedUser.telegram_id,
        username: selectedUser.username,
        type: 'gift',
        amount_usd: amtUSD,
        amount_syp: amtSYP,
        exchange_rate: exchangeRate,
        status: 'completed',
        notes: language === 'ar' ? 'هدية من الإدمن' : 'Admin gift',
      });

      setActionMsg({ type: 'success', text: language === 'ar' ? 'تم إهداء الرصيد بنجاح' : 'Balance gifted successfully' });
      setSelectedUser({ ...selectedUser, balance_syp: selectedUser.balance_syp + amtSYP });
      loadUsers();

    } catch (err) {
      console.error("Gift error:", err);
      setActionMsg({ type: 'error', text: language === 'ar' ? 'حدث خطأ' : 'An error occurred' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleWithdraw = async () => {
    if (!selectedUser || !amount) return;
    setActionLoading(true);
    try {
      const amtSYP = amountType === 'usd' ? Number(amount) * exchangeRate : Number(amount);
      const amtUSD = amountType === 'usd' ? Number(amount) : Number(amount) / exchangeRate;

      if (amtSYP > selectedUser.balance_syp) {
        setActionMsg({ type: 'error', text: language === 'ar' ? 'رصيد المستخدم غير كافٍ' : 'Insufficient user balance' });
        setActionLoading(false);
        return;
      }

      await supabase.from('users').update({
        balance_syp: selectedUser.balance_syp - amtSYP,
        balance_usd: selectedUser.balance_usd - amtUSD,
        operations_count: selectedUser.operations_count + 1,
      }).eq('id', selectedUser.id);

      const { data: bal } = await supabase.from('bot_balance').select('*').maybeSingle();
      if (bal) {
        await supabase.from('bot_balance').update({
          balance_syp: bal.balance_syp + amtSYP,
          balance_usd: bal.balance_usd + amtUSD,
          updated_at: new Date().toISOString(),
        }).eq('id', bal.id);
      }

      await supabase.from('transactions').insert({
        user_id: selectedUser.id,
        telegram_id: selectedUser.telegram_id,
        username: selectedUser.username,
        type: 'admin_withdraw',
        amount_usd: amtUSD,
        amount_syp: amtSYP,
        exchange_rate: exchangeRate,
        status: 'completed',
        notes: language === 'ar' ? 'سحب إداري' : 'Admin withdrawal',
      });

      setActionMsg({ type: 'success', text: language === 'ar' ? 'تم سحب الرصيد بنجاح' : 'Balance withdrawn successfully' });
      setSelectedUser({ ...selectedUser, balance_syp: selectedUser.balance_syp - amtSYP });
      loadUsers();

    } catch (err) {
      console.error("Withdraw error:", err);
      setActionMsg({ type: 'error', text: language === 'ar' ? 'حدث خطأ' : 'An error occurred' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleBlock = async () => {
    if (!selectedUser) return;
    setActionLoading(true);
    try {
      const { error } = await supabase.from('users')
        .update({ is_blocked: !selectedUser.is_blocked })
        .eq('id', selectedUser.id);

      if (error) throw error;

      setActionMsg({
        type: 'success',
        text: selectedUser.is_blocked
          ? (language === 'ar' ? 'تم رفع الحظر' : 'User unblocked')
          : (language === 'ar' ? 'تم حظر المستخدم' : 'User blocked')
      });

      setSelectedUser({ ...selectedUser, is_blocked: !selectedUser.is_blocked });
      loadUsers();

    } catch (err) {
      console.error("Block error:", err);
      setActionMsg({ type: 'error', text: language === 'ar' ? 'حدث خطأ' : 'An error occurred' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    if (!confirm(
      language === 'ar' 
        ? `هل أنت متأكد من حذف المستخدم "${selectedUser.username}"؟ لا يمكن التراجع عن هذا الإجراء.`
        : `Are you sure you want to delete user "${selectedUser.username}"? This action cannot be undone.`
    )) {
      return;
    }

    setActionLoading(true);
    try {
      // Delete user transactions first
      await supabase.from('transactions').delete().eq('user_id', selectedUser.id);
      
      // Delete the user
      const { error } = await supabase.from('users').delete().eq('id', selectedUser.id);

      if (error) throw error;

      setActionMsg({
        type: 'success',
        text: language === 'ar' ? `تم حذف المستخدم "${selectedUser.username}" بنجاح` : `User "${selectedUser.username}" deleted successfully`
      });

      setSelectedUser(null);
      setModalMode(null);
      loadUsers();

    } catch (err) {
      console.error("Delete error:", err);
      setActionMsg({
        type: 'error', 
        text: language === 'ar' ? 'فشل حذف المستخدم' : 'Failed to delete user'
      });
    } finally {
      setActionLoading(false);
    }
  };

  const fmt = (n: number) => new Intl.NumberFormat().format(Math.round(n));
  const totalPages = Math.ceil(total / PAGE_SIZE);

  
  const inputCls = `w-full px-3 py-2 rounded-xl text-sm border outline-none transition-colors
    ${isDark ? 'bg-slate-800 border-slate-600 text-white placeholder-slate-500 focus:border-blue-500' : 'bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:border-blue-500'}`;

  const btnBase = `px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 whitespace-nowrap`;

  return (
    <div className="space-y-4">
      <div className={`rounded-2xl border p-4 ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-48">
            <Search size={14} className={`absolute top-1/2 -translate-y-1/2 ${language === 'ar' ? 'right-3' : 'left-3'} ${isDark ? 'text-slate-400' : 'text-slate-400'}`} />
            <input
              value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
              placeholder={t(language, 'search')}
              className={`${inputCls} ${language === 'ar' ? 'pr-9' : 'pl-9'}`}
            />
          </div>
          <div className={`flex rounded-xl overflow-hidden border ${isDark ? 'border-slate-600' : 'border-slate-200'}`}>
            {(['all', 'active', 'blocked'] as const).map(s => (
              <button key={s} onClick={() => { setFilterStatus(s); setPage(1); }}
                className={`px-3 py-2 text-xs font-medium transition-colors
                  ${filterStatus === s ? 'bg-blue-600 text-white' : isDark ? 'bg-slate-800 text-slate-400 hover:text-white' : 'bg-white text-slate-500 hover:text-slate-700'}`}>
                {t(language, s)}
              </button>
            ))}
          </div>
          <button onClick={loadUsers} className={`${btnBase} ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            <RefreshCw size={12} /> {t(language, 'refresh')}
          </button>
        </div>
      </div>

      <div className={`rounded-2xl border overflow-hidden ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className={`text-xs ${isDark ? 'bg-slate-900/50 text-slate-400' : 'bg-slate-50 text-slate-500'}`}>
                {[t(language,'telegramId'), t(language,'username'), t(language,'firstName'), t(language,'sypBalance'), t(language,'status'), t(language,'operations'), t(language,'actions')]
                  .map(h => <th key={h} className="px-4 py-3 font-medium text-start whitespace-nowrap">{h}</th>)}
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-slate-700/30' : 'divide-slate-100'}`}>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className={`h-4 rounded animate-pulse ${isDark ? 'bg-slate-700' : 'bg-slate-100'}`} style={{ width: `${40 + Math.random() * 40}%` }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr><td colSpan={7} className={`px-4 py-10 text-center text-sm ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{t(language, 'noData')}</td></tr>
              ) : users.map(u => (
                <tr key={u.id} className={`transition-colors ${isDark ? 'hover:bg-slate-700/30' : 'hover:bg-slate-50'}`}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{u.telegram_id}</td>
                  <td className={`px-4 py-3 font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>@{u.username || '—'}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>{u.first_name || '—'}</td>
                  <td className={`px-4 py-3 font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>{fmt(u.balance_syp)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
                      ${u.is_blocked ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/15 text-emerald-400'}`}>
                      {u.is_blocked ? <XCircle size={10} /> : <CheckCircle size={10} />}
                      {t(language, u.is_blocked ? 'blocked' : 'active')}
                    </span>
                  </td>
                  <td className={`px-4 py-3 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{u.operations_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => openModal(u, 'view')} title={t(language, 'operationsLog')}
                        className={`${btnBase} ${isDark ? 'bg-slate-700 text-blue-400 hover:bg-slate-600' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'}`}>
                        <Eye size={11} />
                      </button>
                      <button onClick={() => openModal(u, 'gift')} title={t(language, 'giftBalance')}
                        className={`${btnBase} ${isDark ? 'bg-slate-700 text-emerald-400 hover:bg-slate-600' : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'}`}>
                        <Gift size={11} />
                      </button>
                      <button onClick={() => openModal(u, 'withdraw')} title={t(language, 'withdrawBalance')}
                        className={`${btnBase} ${isDark ? 'bg-slate-700 text-amber-400 hover:bg-slate-600' : 'bg-amber-50 text-amber-600 hover:bg-amber-100'}`}>
                        <ArrowUpFromLine size={11} />
                      </button>
                      <button onClick={() => openModal(u, 'block')} title={u.is_blocked ? t(language, 'unblock') : t(language, 'block')}
                        className={`${btnBase} ${u.is_blocked ? (isDark ? 'bg-slate-700 text-emerald-400 hover:bg-slate-600' : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100') : (isDark ? 'bg-slate-700 text-red-400 hover:bg-slate-600' : 'bg-red-50 text-red-600 hover:bg-red-100')}`}>
                        <Ban size={11} />
                      </button>
                      <button onClick={() => openModal(u, 'changePassword')}
                        className={`${btnBase} ${isDark ? 'bg-slate-700 text-slate-400 hover:bg-slate-600' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}>
                        <Lock size={11} />
                      </button>
                      <button onClick={() => openModal(u, 'delete')} title={language === 'ar' ? 'حذف المستخدم' : 'Delete User'}
                        className={`${btnBase} ${isDark ? 'bg-red-900/20 text-red-400 hover:bg-red-900/30' : 'bg-red-50 text-red-600 hover:bg-red-100'}`}>
                        <XCircle size={11} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={`flex items-center justify-between px-4 py-3 border-t text-xs ${isDark ? 'border-slate-700/40 text-slate-400' : 'border-slate-100 text-slate-500'}`}>
          <span>{language === 'ar' ? `${total} مستخدم — صفحة ${page} من ${totalPages || 1}` : `${total} users — Page ${page} of ${totalPages || 1}`}</span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className={`p-1.5 rounded-lg transition-colors ${page === 1 ? 'opacity-30 cursor-not-allowed' : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}>
              {language === 'ar' ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              className={`p-1.5 rounded-lg transition-colors ${page >= totalPages ? 'opacity-30 cursor-not-allowed' : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}>
              {language === 'ar' ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
            </button>
          </div>
        </div>
      </div>

      <Modal isOpen={modalMode === 'view' && !!selectedUser} onClose={closeModal}
        title={`${t(language, 'operationsLog')} — @${selectedUser?.username || selectedUser?.telegram_id}`}
        maxWidth="max-w-2xl">
        {selectedUser && (
          <div className="space-y-4">
            <div className={`grid grid-cols-2 gap-3`}>
              {[
                { label: t(language, 'telegramId'), value: String(selectedUser.telegram_id) },
                { label: t(language, 'sypBalance'), value: `${fmt(selectedUser.balance_syp)} ${t(language, 'syp')}` },
                { label: t(language, 'totalDeposits'), value: `${fmt(selectedUser.total_deposits)} ${t(language, 'syp')}` },
                { label: t(language, 'operations'), value: String(selectedUser.operations_count) },
              ].map(({ label, value }) => (
                <div key={label} className={`rounded-xl p-3 ${isDark ? 'bg-slate-800' : 'bg-slate-50'}`}>
                  <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{label}</p>
                  <p className={`text-sm font-semibold mt-0.5 ${isDark ? 'text-white' : 'text-slate-800'}`}>{value}</p>
                </div>
              ))}
            </div>
            <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-slate-700' : 'border-slate-200'}`}>
              <table className="w-full text-xs">
                <thead>
                  <tr className={isDark ? 'bg-slate-900/50 text-slate-400' : 'bg-slate-50 text-slate-500'}>
                    {['#', t(language, 'type'), t(language, 'amountSYP'), t(language, 'date')].map(h => (
                      <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className={`divide-y ${isDark ? 'divide-slate-700/30' : 'divide-slate-100'}`}>
                  {userTxs.length === 0 ? (
                    <tr><td colSpan={4} className={`px-3 py-4 text-center ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{t(language, 'noData')}</td></tr>
                  ) : userTxs.map((tx, i) => (
                    <tr key={tx.id} className={isDark ? 'hover:bg-slate-700/20' : 'hover:bg-slate-50'}>
                      <td className={`px-3 py-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{tx.operation_number || i + 1}</td>
                      <td className="px-3 py-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium
                          ${tx.type === 'deposit' ? 'bg-emerald-500/15 text-emerald-400'
                          : tx.type === 'withdrawal' ? 'bg-red-500/15 text-red-400'
                          : tx.type === 'gift' ? 'bg-blue-500/15 text-blue-400'
                          : 'bg-amber-500/15 text-amber-400'}`}>
                          {t(language, tx.type === 'deposit' ? 'deposit' : tx.type === 'withdrawal' ? 'withdrawal' : tx.type === 'gift' ? 'gift' : 'adminWithdraw')}
                        </span>
                      </td>
                      <td className={`px-3 py-2 font-medium ${tx.type === 'deposit' || tx.type === 'gift' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {tx.type === 'deposit' || tx.type === 'gift' ? '+' : '-'}{fmt(tx.amount_syp)}
                      </td>
                      <td className={`px-3 py-2 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                        {new Date(tx.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className={`flex items-center justify-between px-3 py-2 border-t text-xs ${isDark ? 'border-slate-700/40 text-slate-500' : 'border-slate-100 text-slate-400'}`}>
                <span>{txTotal} {language === 'ar' ? 'عملية' : 'operations'}</span>
                <div className="flex gap-1">
                  <button onClick={() => setTxPage(p => Math.max(1, p - 1))} disabled={txPage === 1} className={`p-1 rounded ${txPage === 1 ? 'opacity-30' : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}>
                    {language === 'ar' ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
                  </button>
                  <button onClick={() => setTxPage(p => p + 1)} disabled={txPage * 10 >= txTotal} className={`p-1 rounded ${txPage * 10 >= txTotal ? 'opacity-30' : isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'}`}>
                    {language === 'ar' ? <ChevronLeft size={12} /> : <ChevronRight size={12} />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>

      <Modal isOpen={(modalMode === 'gift' || modalMode === 'withdraw') && !!selectedUser} onClose={closeModal}
        title={modalMode === 'gift' ? `${t(language, 'giftBalance')} — @${selectedUser?.username}` : `${t(language, 'withdrawBalance')} — @${selectedUser?.username}`}>
        {selectedUser && (
          <div className="space-y-4">
            <div className={`rounded-xl p-3 ${isDark ? 'bg-slate-800' : 'bg-slate-50'}`}>
              <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{t(language, 'sypBalance')}</p>
              <p className={`text-lg font-bold ${isDark ? 'text-white' : 'text-slate-800'}`}>{fmt(selectedUser.balance_syp)} {t(language, 'syp')}</p>
            </div>
            <div className="flex gap-2">
              {(['syp', 'usd'] as const).map(tp => (
                <button key={tp} onClick={() => setAmountType(tp)}
                  className={`flex-1 py-2 rounded-xl text-sm font-medium transition-colors
                    ${amountType === tp ? 'bg-blue-600 text-white' : isDark ? 'bg-slate-800 text-slate-400 hover:text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                  {tp === 'syp' ? t(language, 'syp') : t(language, 'usd')}
                </button>
              ))}
            </div>
            <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
              placeholder={t(language, 'enterAmount')} className={`w-full px-4 py-3 rounded-xl text-sm border outline-none
                ${isDark ? 'bg-slate-800 border-slate-600 text-white placeholder-slate-500 focus:border-blue-500' : 'bg-slate-50 border-slate-200 text-slate-800 focus:border-blue-500'}`} />
            {amountType === 'usd' && amount && (
              <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                ≈ {fmt(Number(amount) * exchangeRate)} {t(language, 'syp')}
              </p>
            )}
            {actionMsg && (
              <div className={`flex items-center gap-2 p-3 rounded-xl text-sm ${actionMsg.type === 'success' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                {actionMsg.type === 'success' ? <CheckCircle size={14} /> : <XCircle size={14} />}
                {actionMsg.text}
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={closeModal} className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{t(language, 'cancel')}</button>
              <button onClick={modalMode === 'gift' ? handleGift : handleWithdraw} disabled={actionLoading || !amount}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors text-white
                  ${modalMode === 'gift' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-amber-600 hover:bg-amber-700'}
                  ${actionLoading || !amount ? 'opacity-50 cursor-not-allowed' : ''}`}>
                {actionLoading ? t(language, 'loading') : t(language, 'confirm')}
              </button>
            </div>
          </div>
        )}
      </Modal>

      <Modal isOpen={modalMode === 'block' && !!selectedUser} onClose={closeModal}
        title={selectedUser?.is_blocked ? t(language, 'confirmUnblock') : t(language, 'confirmBlock')}>
        {selectedUser && (
          <div className="space-y-4">
            <p className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
              {t(language, 'areYouSure')} {selectedUser.is_blocked
                ? (language === 'ar' ? `رفع حظر @${selectedUser.username}؟` : `unblock @${selectedUser.username}?`)
                : (language === 'ar' ? `حظر @${selectedUser.username}؟` : `block @${selectedUser.username}?`)}
            </p>
            {actionMsg && (
              <div className={`flex items-center gap-2 p-3 rounded-xl text-sm ${actionMsg.type === 'success' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                {actionMsg.type === 'success' ? <CheckCircle size={14} /> : <XCircle size={14} />}
                {actionMsg.text}
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={closeModal} className={`flex-1 py-2.5 rounded-xl text-sm font-medium ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{t(language, 'cancel')}</button>
              <button onClick={handleToggleBlock} disabled={actionLoading}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium text-white transition-colors
                  ${selectedUser.is_blocked ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}
                  ${actionLoading ? 'opacity-50 cursor-not-allowed' : ''}`}>
                {actionLoading ? t(language, 'loading') : t(language, 'confirm')}
              </button>
            </div>
          </div>
        )}
      </Modal>

      <Modal isOpen={modalMode === 'delete' && !!selectedUser} onClose={closeModal}
        title={language === 'ar' ? `حذف المستخدم ${selectedUser?.username}` : `Delete User ${selectedUser?.username}`}>
        {selectedUser && (
          <div className="space-y-4">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-red-900/20 border border-red-500/30' : 'bg-red-50 border-red-200'}`}>
              <p className={`text-sm ${isDark ? 'text-red-300' : 'text-red-700'}`}>
                {language === 'ar' 
                  ? `هل أنت متأكد من حذف المستخدم "${selectedUser.username}"؟ سيتم حذف جميع بياناته ومعاملاته بشكل نهائي ولا يمكن التراجع عن هذا الإجراء.`
                  : `Are you sure you want to delete user "${selectedUser.username}"? All their data and transactions will be permanently deleted and this action cannot be undone.`
                }
              </p>
            </div>
            {actionMsg && (
              <div className={`flex items-center gap-2 p-3 rounded-xl text-sm ${actionMsg.type === 'success' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                {actionMsg.type === 'success' ? <CheckCircle size={14} /> : <XCircle size={14} />}
                {actionMsg.text}
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={closeModal} className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors ${isDark ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                {language === 'ar' ? 'إلغاء' : 'Cancel'}
              </button>
              <button onClick={handleDeleteUser} disabled={actionLoading}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium text-white transition-colors bg-red-600 hover:bg-red-700 ${actionLoading ? 'opacity-50 cursor-not-allowed' : ''}`}>
                {actionLoading ? (language === 'ar' ? 'جاري الحذف...' : 'Deleting...') : (language === 'ar' ? 'حذف المستخدم' : 'Delete User')}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
