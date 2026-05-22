import { useState, useEffect, useCallback } from 'react';
import { Users, TrendingDown, TrendingUp, MessageSquare, DollarSign, RefreshCw, Activity, Zap } from 'lucide-react';
import { useApp } from '../contexts/GlobalContext';
import { supabase } from '../lib/supabase';
import { t } from '../lib/i18n';
import { useDashboardRealtime } from '../hooks/useRealtime';
import SparklineChart, { BarChart } from '../components/charts/SparklineChart';

interface Stats {
  activeUsers: number;
  totalUsers: number;
  balanceSYP: number;
  balanceUSD: number;
  botAdminBalance: number;  // 🔥 رصيد البوت الرئيسي
  weekDeposits: number;
  weekWithdrawals: number;
  weekMessages: number;
  monthDeposits: number;
  monthWithdrawals: number;
  exchangeRate: number;
  depositTrend: number[];
  withdrawalTrend: number[];
  usersTrend: number[];
  messageTrend: number[];
  weeklyDepositsChart: { label: string; value: number }[];
  weeklyWithdrawalsChart: { label: string; value: number }[];
  monthlyDepositsChart: { label: string; value: number }[];
  monthlyWithdrawalsChart: { label: string; value: number }[];
  recentTransactions: RecentTx[];
  todayDeposits: number;
  todayWithdrawals: number;
}

interface RecentTx {
  id: string;
  type: string;
  username: string;
  amount_syp: number;
  created_at: string;
}

function StatCard({ icon: Icon, label, value, subLabel, trend, sparkData, color, isDark, change }: {
  icon: React.ElementType; label: string; value: string; subLabel?: string;
  trend?: 'up' | 'down' | 'neutral'; sparkData: number[]; color: string;
  isDark: boolean; change?: string;
}) {
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-400';
  return (
    <div className={`rounded-lg p-2.5 border relative overflow-hidden transition-all duration-300 hover:scale-[1.01] hover:shadow-md group
      ${isDark ? 'bg-slate-800/70 border-slate-700/40 hover:border-slate-600' : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-slate-200'}
    `}>
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: `radial-gradient(circle at 80% 20%, ${color}08 0%, transparent 60%)` }} />
      <div className="flex items-start justify-between mb-1.5">
        <div className={`w-6 h-6 rounded-md flex items-center justify-center`} style={{ backgroundColor: `${color}18` }}>
          <Icon size={12} style={{ color }} />
        </div>
        <div className="opacity-60">
          <SparklineChart data={sparkData} color={color} height={24} width={48} />
        </div>
      </div>
      <p className={`text-[9px] font-medium mb-0.5 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{label}</p>
      <p className={`text-sm font-bold ${isDark ? 'text-white' : 'text-slate-800'}`}>{value}</p>
      {(subLabel || change) && (
        <div className="flex items-center gap-1 mt-0.5">
          {change && <span className={`text-[9px] font-medium ${trendColor}`}>{change}</span>}
          {subLabel && <span className={`text-[9px] ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{subLabel}</span>}
        </div>
      )}
    </div>
  );
}

const DAY_LABELS_AR = ['السبت', 'الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة'];
const DAY_LABELS_EN = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

function generateWeekLabels(lang: 'ar' | 'en') {
  const labels = lang === 'ar' ? DAY_LABELS_AR : DAY_LABELS_EN;
  const today = new Date().getDay();
  return Array.from({ length: 7 }, (_, i) => labels[(today - 6 + i + 7) % 7]);
}

function generateMonthLabels(lang: 'ar' | 'en') {
  const today = new Date();
  const labels = [];
  
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(today.getDate() - i);
    if (lang === 'ar') {
      labels.unshift(`${date.getDate()} ${['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'][date.getMonth()]}`);
    } else {
      labels.unshift(`${date.getMonth() + 1}/${date.getDate()}`);
    }
  }
  
  return labels;
}

export default function DashboardPage() {
  const { theme, language, exchangeRate } = useApp();
  const isDark = theme === 'dark';
  const [stats, setStats] = useState<Stats>({
    activeUsers: 0, totalUsers: 0, balanceSYP: 0, balanceUSD: 0, botAdminBalance: 0,  // 🔥
    weekDeposits: 0, weekWithdrawals: 0, weekMessages: 0,
    monthDeposits: 0, monthWithdrawals: 0,
    exchangeRate: exchangeRate,
    depositTrend: [0, 0, 0, 0, 0, 0, 0],
    withdrawalTrend: [0, 0, 0, 0, 0, 0, 0],
    usersTrend: [0, 0, 0, 0, 0, 0, 0],
    messageTrend: [0, 0, 0, 0, 0, 0, 0],
    weeklyDepositsChart: [],
    weeklyWithdrawalsChart: [],
    monthlyDepositsChart: [],
    monthlyWithdrawalsChart: [],
    recentTransactions: [],
    todayDeposits: 0,
    todayWithdrawals: 0,
  });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const loadStats = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString();
      const monthAgo = new Date(Date.now() - 30 * 86400000).toISOString();
      const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);

      const BOT_ADMIN_ID = 7179419936;  // 🔥 معرف البوت الرئيسي

      const [usersRes, balanceRes, botAdminRes, txRes, msgRes, recentTxRes] = await Promise.all([
        supabase.from('users').select('id, created_at, last_active, is_blocked'),
        supabase.from('bot_balance').select('balance_syp, balance_usd').maybeSingle(),
        supabase.from('users').select('balance_syp').eq('telegram_id', BOT_ADMIN_ID).maybeSingle(),  // 🔥 رصيد البوت
        supabase.from('transactions').select('type, amount_syp, created_at').gte('created_at', monthAgo),
        supabase.from('messages').select('id, created_at').eq('direction', 'incoming').gte('created_at', weekAgo),
        supabase.from('transactions').select('id, type, username, amount_syp, created_at').order('created_at', { ascending: false }).limit(8),
      ]);

      const users = usersRes.data || [];
      const balance = balanceRes.data;
      const botAdminBalance = botAdminRes.data?.balance_syp || 0;  // 🔥 رصيد البوت
      const txs = txRes.data || [];
      const msgs = msgRes.data || [];

      const weekAgoDate = new Date(weekAgo);
      const monthAgoDate = new Date(monthAgo);
      const activeUsers = users.filter(u => new Date(u.last_active) >= weekAgoDate).length;

      const deposits = txs.filter(tx => tx.type === 'deposit');
      const withdrawals = txs.filter(tx => tx.type === 'withdrawal');
      
      // Weekly calculations
      const weekDeposits = deposits.reduce((s, d) => s + Number(d.amount_syp), 0);
      const weekWithdrawals = withdrawals.reduce((s, d) => s + Number(d.amount_syp), 0);
      
      // Monthly calculations
      const monthDeposits = deposits.reduce((s, d) => s + Number(d.amount_syp), 0);
      const monthWithdrawals = withdrawals.reduce((s, d) => s + Number(d.amount_syp), 0);

      const weekLabels = generateWeekLabels(language);
      const monthLabels = generateMonthLabels(language);
      const depositByDay = Array(7).fill(0);
      const withdrawByDay = Array(7).fill(0);
      const usersByDay = Array(7).fill(0);
      const msgsByDay = Array(7).fill(0);
      const depositByMonth = Array(30).fill(0);
      const withdrawByMonth = Array(30).fill(0);

      txs.forEach(tx => {
        const dayIdx = Math.floor((Date.now() - new Date(tx.created_at).getTime()) / 86400000);
        const monthIdx = Math.floor((Date.now() - new Date(tx.created_at).getTime()) / 86400000);
        if (dayIdx >= 0 && dayIdx < 7) {
          if (tx.type === 'deposit') depositByDay[6 - dayIdx] += Number(tx.amount_syp);
          if (tx.type === 'withdrawal') withdrawByDay[6 - dayIdx] += Number(tx.amount_syp);
        }
        if (monthIdx >= 0 && monthIdx < 30) {
          if (tx.type === 'deposit') depositByMonth[29 - monthIdx] += Number(tx.amount_syp);
          if (tx.type === 'withdrawal') withdrawByMonth[29 - monthIdx] += Number(tx.amount_syp);
        }
      });
      users.forEach(u => {
        const dayIdx = Math.floor((Date.now() - new Date(u.created_at).getTime()) / 86400000);
        if (dayIdx >= 0 && dayIdx < 7) usersByDay[6 - dayIdx]++;
      });
      msgs.forEach(m => {
        const dayIdx = Math.floor((Date.now() - new Date(m.created_at).getTime()) / 86400000);
        if (dayIdx >= 0 && dayIdx < 7) msgsByDay[6 - dayIdx]++;
      });

      const todayTxs = txs.filter(tx => new Date(tx.created_at) >= todayStart);
      const todayDeposits = todayTxs.filter(tx => tx.type === 'deposit').reduce((s, d) => s + Number(d.amount_syp), 0);
      const todayWithdrawals = todayTxs.filter(tx => tx.type === 'withdrawal').reduce((s, d) => s + Number(d.amount_syp), 0);

      setStats({
        activeUsers,
        totalUsers: users.length,
        balanceSYP: balance?.balance_syp || 0,
        balanceUSD: balance?.balance_usd || 0,
        botAdminBalance,  // 🔥 رصيد البوت الرئيسي
        weekDeposits,
        weekWithdrawals,
        weekMessages: msgs.length,
        monthDeposits,
        monthWithdrawals,
        exchangeRate,
        depositTrend: depositByDay,
        withdrawalTrend: withdrawByDay,
        usersTrend: usersByDay,
        messageTrend: msgsByDay,
        weeklyDepositsChart: weekLabels.map((label, i) => ({ label, value: depositByDay[i] })),
        weeklyWithdrawalsChart: weekLabels.map((label, i) => ({ label, value: withdrawByDay[i] })),
        monthlyDepositsChart: monthLabels.map((label, i) => ({ label, value: depositByMonth[i] })),
        monthlyWithdrawalsChart: monthLabels.map((label, i) => ({ label, value: withdrawByMonth[i] })),
        recentTransactions: recentTxRes.data || [],
        todayDeposits,
        todayWithdrawals,
      });
      setLastUpdated(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, [language, exchangeRate]);

  useEffect(() => { loadStats(); }, [loadStats]);
  useDashboardRealtime(loadStats);

  const fmt = (n: number) => new Intl.NumberFormat(language === 'ar' ? 'ar-SY' : 'en-US').format(Math.round(n));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            {language === 'ar' ? 'آخر تحديث:' : 'Last updated:'} {lastUpdated.toLocaleTimeString(language === 'ar' ? 'ar-SA' : 'en-US')}
          </p>
        </div>
        <button
          onClick={loadStats}
          disabled={isRefreshing}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-all
            ${isDark ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'}
          `}
        >
          <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
          {t(language, 'refresh')}
        </button>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-6 gap-2.5">
        <StatCard
          icon={Users} label={`${t(language, 'activeUsers')} — ${t(language, 'thisWeek')}`}
          value={fmt(stats.activeUsers)} subLabel={`${t(language, 'totalUsers')}: ${fmt(stats.totalUsers)}`}
          sparkData={stats.usersTrend} color="#3b82f6" isDark={isDark}
          trend="up" change={`+${stats.activeUsers}`}
        />
        {/* 🔥 الرصيد العام للبوت - رصيد JADO BOT ADMIN */}
        <StatCard
          icon={DollarSign} label={t(language, 'botBalance')}
          value={`${fmt(stats.botAdminBalance)} ${t(language, 'syp')}`}
          subLabel={`$${(stats.botAdminBalance / exchangeRate).toFixed(2)}`}
          sparkData={stats.depositTrend.map((d, i) => d - stats.withdrawalTrend[i])}
          color="#10b981" isDark={isDark}
        />
        <StatCard
          icon={TrendingDown} label={t(language, 'weeklyDeposits')}
          value={`${fmt(stats.weekDeposits)} ${t(language, 'syp')}`}
          subLabel={`${language === 'ar' ? 'اليوم:' : 'Today:'} ${fmt(stats.todayDeposits)}`}
          sparkData={stats.depositTrend} color="#10b981" isDark={isDark}
          trend="up"
        />
        <StatCard
          icon={TrendingUp} label={t(language, 'weeklyWithdrawals')}
          value={`${fmt(stats.weekWithdrawals)} ${t(language, 'syp')}`}
          subLabel={`${language === 'ar' ? 'اليوم:' : 'Today:'} ${fmt(stats.todayWithdrawals)}`}
          sparkData={stats.withdrawalTrend} color="#ef4444" isDark={isDark}
          trend="down"
        />
        <StatCard
          icon={TrendingDown} label={t(language, 'monthlyDeposits')}
          value={`${fmt(stats.monthDeposits)} ${t(language, 'syp')}`}
          subLabel={`${language === 'ar' ? 'الشهري:' : 'Monthly:'} ${fmt(stats.monthDeposits)}`}
          sparkData={stats.monthlyDepositsChart.map(d => d.value).slice(-7)} color="#3b82f6" isDark={isDark}
          trend="up"
        />
        <StatCard
          icon={TrendingUp} label={t(language, 'monthlyWithdrawals')}
          value={`${fmt(stats.monthWithdrawals)} ${t(language, 'syp')}`}
          subLabel={`${language === 'ar' ? 'الشهري:' : 'Monthly:'} ${fmt(stats.monthWithdrawals)}`}
          sparkData={stats.monthlyWithdrawalsChart.map(d => d.value).slice(-7)} color="#ef4444" isDark={isDark}
          trend="down"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <StatCard
          icon={MessageSquare} label={t(language, 'incomingMessages')}
          value={fmt(stats.weekMessages)} subLabel={t(language, 'thisWeek')}
          sparkData={stats.messageTrend} color="#f59e0b" isDark={isDark}
        />
        <div className={`rounded-2xl p-5 border flex flex-col gap-3
          ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}
        `}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/15 flex items-center justify-center">
              <Activity size={20} className="text-sky-400" />
            </div>
            <div>
              <p className={`text-xs font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{t(language, 'exchangeRate')}</p>
              <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-800'}`}>
                {fmt(exchangeRate)} <span className={`text-sm font-normal ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{t(language, 'syp')}</span>
              </p>
            </div>
          </div>
          <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
            {language === 'ar' ? '1 دولار = ' : '1 USD = '}{fmt(exchangeRate)}{' '}{t(language, 'syp')}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`rounded-2xl p-5 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
          <p className={`text-sm font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-800'}`}>
            <span className="inline-flex items-center gap-2">
              <TrendingDown size={14} className="text-emerald-400" />
              {language === 'ar' ? 'إيداعات الأسبوع' : 'Weekly Deposits'} — {t(language, 'syp')}
            </span>
          </p>
          <BarChart data={stats.weeklyDepositsChart} color="#10b981" height={110} />
        </div>
        <div className={`rounded-2xl p-5 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
          <p className={`text-sm font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-800'}`}>
            <span className="inline-flex items-center gap-2">
              <TrendingUp size={14} className="text-red-400" />
              {language === 'ar' ? 'سحوبات الأسبوع' : 'Weekly Withdrawals'} — {t(language, 'syp')}
            </span>
          </p>
          <BarChart data={stats.weeklyWithdrawalsChart} color="#ef4444" height={110} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`rounded-2xl p-5 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
          <p className={`text-sm font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-800'}`}>
            <span className="inline-flex items-center gap-2">
              <TrendingDown size={14} className="text-blue-400" />
              {language === 'ar' ? 'إيداعات الشهرية' : 'Monthly Deposits'} — {t(language, 'syp')}
            </span>
          </p>
          <BarChart data={stats.monthlyDepositsChart} color="#3b82f6" height={110} />
        </div>
        <div className={`rounded-2xl p-5 border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
          <p className={`text-sm font-semibold mb-4 ${isDark ? 'text-white' : 'text-slate-800'}`}>
            <span className="inline-flex items-center gap-2">
              <TrendingUp size={14} className="text-orange-400" />
              {language === 'ar' ? 'سحوبات الشهرية' : 'Monthly Withdrawals'} — {t(language, 'syp')}
            </span>
          </p>
          <BarChart data={stats.monthlyWithdrawalsChart} color="#f97316" height={110} />
        </div>
      </div>

      <div className={`rounded-2xl border ${isDark ? 'bg-slate-800/70 border-slate-700/40' : 'bg-white border-slate-200'}`}>
        <div className={`px-5 py-4 border-b ${isDark ? 'border-slate-700/40' : 'border-slate-100'}`}>
          <p className={`text-sm font-semibold flex items-center gap-2 ${isDark ? 'text-white' : 'text-slate-800'}`}>
            <Zap size={14} className="text-amber-400" />
            {t(language, 'recentActivity')}
          </p>
        </div>
        <div className="divide-y divide-slate-700/20">
          {stats.recentTransactions.length === 0 ? (
            <p className={`px-5 py-8 text-center text-sm ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>{t(language, 'noData')}</p>
          ) : stats.recentTransactions.map(tx => (
            <div key={tx.id} className={`flex items-center justify-between px-5 py-3 hover:${isDark ? 'bg-slate-700/20' : 'bg-slate-50'} transition-colors`}>
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold
                  ${tx.type === 'deposit' ? 'bg-emerald-500/15 text-emerald-400'
                    : tx.type === 'withdrawal' ? 'bg-red-500/15 text-red-400'
                    : tx.type === 'gift' ? 'bg-blue-500/15 text-blue-400'
                    : 'bg-slate-500/15 text-slate-400'}`}>
                  {tx.type === 'deposit' ? '↓' : tx.type === 'withdrawal' ? '↑' : tx.type === 'gift' ? '♦' : '⊕'}
                </div>
                <div>
                  <p className={`text-sm font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>
                    @{tx.username || '—'}
                  </p>
                  <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {new Date(tx.created_at).toLocaleString(language === 'ar' ? 'ar-SA' : 'en-US', { dateStyle: 'short', timeStyle: 'short' })}
                  </p>
                </div>
              </div>
              <div className="text-end">
                <p className={`text-sm font-semibold ${tx.type === 'deposit' || tx.type === 'gift' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {tx.type === 'deposit' || tx.type === 'gift' ? '+' : '-'}{fmt(tx.amount_syp)} {t(language, 'syp')}
                </p>
                <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                  {language === 'ar' ? t(language, tx.type === 'deposit' ? 'deposit' : tx.type === 'withdrawal' ? 'withdrawal' : tx.type === 'gift' ? 'gift' : 'adminWithdraw') : tx.type}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
