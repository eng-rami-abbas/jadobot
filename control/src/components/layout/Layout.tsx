import { useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import { useApp } from '../../contexts/GlobalContext';
import DashboardPage from '../../pages/DashboardPage';
import UsersPage from '../../pages/UsersPage';
import MessagesPage from '../../pages/MessagesPage';
import DepositsPage from '../../pages/DepositsPage';
import WithdrawalsPage from '../../pages/WithdrawalsPage';
import SettingsPage from '../../pages/SettingsPage';
import EventsPage from '../../pages/EventsPage';
import GiftCodesPage from '../../pages/GiftCodesPage';
import WalletsPage from '../../pages/WalletsPage';
import WithdrawalMethodsPage from '../../pages/WithdrawalMethodsPage';
import BroadcastPage from '../../pages/BroadcastPage';

export default function Layout() {
  const { theme, currentPage } = useApp();
  const isDark = theme === 'dark';
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard': return <DashboardPage />;
      case 'users': return <UsersPage />;
      case 'messages': return <MessagesPage />;
      case 'events': return <EventsPage />;
      case 'deposits': return <DepositsPage />;
      case 'withdrawals': return <WithdrawalsPage />;
      case 'settings': return <SettingsPage />;
      case 'gift-codes': return <GiftCodesPage />;
      case 'broadcast': return <BroadcastPage />;
      case 'wallets': return <WalletsPage />;
      case 'withdrawal-methods': return <WithdrawalMethodsPage />;
      default: return <DashboardPage />;
    }
  };

  return (
    <div className={`flex h-screen overflow-hidden ${isDark ? 'bg-slate-950' : 'bg-slate-50'}`}>
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
