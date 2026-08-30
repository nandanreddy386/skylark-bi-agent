import { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import { checkHealth, refreshCache } from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState('');

  useEffect(() => {
    async function verifyBackend() {
      try {
        const res = await checkHealth();
        setHealth(res);
      } catch (err) {
        setHealth({ status: 'offline' });
      }
    }
    verifyBackend();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    setRefreshMsg('');
    try {
      await refreshCache();
      setRefreshMsg('Cache cleared successfully!');
      setTimeout(() => setRefreshMsg(''), 3000);
    } catch (err) {
      setRefreshMsg('Failed to refresh cache.');
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen max-w-full overflow-hidden p-3 md:p-5 gap-4 bg-gradient-to-br from-surface-950 via-[#0a0f1d] to-[#111827]">
      {/* Header */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center px-6 py-3.5 bg-surface-900/90 border border-surface-800 rounded-2xl backdrop-blur-xl gap-4 shadow-xl flex-shrink-0">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-primary-600 via-primary-500 to-accent flex items-center justify-center shadow-lg shadow-primary-500/25">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-extrabold text-surface-100 tracking-tight flex items-center gap-2.5">
              Skylark Drones <span className="text-xs px-2.5 py-1 rounded-full bg-primary-500/20 text-primary-300 font-bold border border-primary-500/40">BI AGENT</span>
            </h1>
            <p className="text-xs text-surface-400 font-medium">Conversational Monday.com Analytics & Executive Reporting</p>
          </div>
        </div>

        {/* Action Controls & Health */}
        <div className="flex items-center gap-3 self-end sm:self-auto">
          {refreshMsg && (
            <span className="text-xs text-emerald-400 font-semibold animate-pulse">{refreshMsg}</span>
          )}
          
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-800 hover:bg-surface-700 text-surface-200 text-xs font-semibold border border-surface-700 transition-all cursor-pointer disabled:opacity-50 shadow-md"
            title="Clear cached Monday.com data to fetch fresh boards"
          >
            <svg className={`w-3.5 h-3.5 text-accent ${refreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>{refreshing ? 'Refreshing...' : 'Sync Monday.com'}</span>
          </button>

          {/* Status Badge */}
          <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface-950/90 border border-surface-800 text-xs shadow-inner">
            <span className={`w-2.5 h-2.5 rounded-full ${
              health?.status === 'ok' ? 'bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400' : 'bg-rose-500'
            }`}></span>
            <span className="text-surface-200 font-semibold">
              {health?.status === 'ok' ? 'Connected' : 'Backend Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Full height flexible chat container */}
      <main className="flex-1 min-h-0 w-full">
        <ChatInterface />
      </main>
    </div>
  );
}
