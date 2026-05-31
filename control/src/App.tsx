import { AppProvider, useApp } from './contexts/GlobalContext';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';

function AppContent() {
  const { isAuthenticated, isLoading, theme } = useApp();

  if (isLoading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${theme === 'dark' ? 'bg-slate-950' : 'bg-slate-50'}`}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className={`text-sm ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>Loading...</p>
        </div>
      </div>
    );
  }

  return isAuthenticated ? <Layout /> : <LoginPage />;
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
