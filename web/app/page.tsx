'use client';

import { useState, useCallback, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Terminal from '@/components/Terminal';
import Ticker from '@/components/Ticker';
import UserMenu from '@/components/UserMenu';
import SessionsList from '@/components/SessionsList';

// Prompt suggestions based on upcoming games
const PROMPT_SUGGESTIONS = [
  "What are the best NFL bets for this weekend?",
  "Find arbitrage opportunities in today's games",
  "Analyze Josh Allen props vs the Chiefs",
  "Check NHL goalie save props for tonight",
  "What's the sharp money saying about the Bills?",
  "Get injury updates for the Eagles",
];

function HomeContent() {
  const searchParams = useSearchParams();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [tickerMessage, setTickerMessage] = useState<string | null>(null);
  const [sessionRefreshTrigger, setSessionRefreshTrigger] = useState(0);

  // Load session from URL query parameter
  useEffect(() => {
    const sessionFromUrl = searchParams.get('session');
    if (sessionFromUrl) {
      setActiveSessionId(sessionFromUrl);
    }
  }, [searchParams]);

  const handleGameClick = useCallback((game: any, prompt: string) => {
    setTickerMessage(prompt);
  }, []);

  const handleTickerMessageHandled = useCallback(() => {
    setTickerMessage(null);
  }, []);

  const handleSessionChange = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
    // Trigger refresh of sessions list
    setSessionRefreshTrigger(prev => prev + 1);
  }, []);

  const handleNewSession = useCallback(() => {
    setActiveSessionId(null);
  }, []);

  const handleSessionSelect = useCallback((sessionId: string | null) => {
    setActiveSessionId(sessionId);
  }, []);

  const handlePromptClick = (prompt: string) => {
    // Start a new session with this prompt
    setActiveSessionId(null);
    // Use ticker message mechanism to send the prompt
    setTickerMessage(prompt);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header with Ticker */}
      <header className="border-b border-terminal-border bg-terminal-surface">
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-terminal-accent glow-green">
              JohnnyBets
            </h1>
            <span className="badge badge-free text-xs">BETA</span>
          </div>
          <nav className="flex items-center gap-4">
            <a 
              href="/tools" 
              className="text-terminal-muted hover:text-terminal-accent transition-colors text-sm"
            >
              Tools
            </a>
            <UserMenu />
          </nav>
        </div>
        
        {/* Live Scores Ticker */}
        <Ticker onGameClick={handleGameClick} />
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Terminal */}
        <div className="flex-1 flex flex-col">
          <Terminal 
            activeSessionId={activeSessionId}
            onSessionChange={handleSessionChange}
            externalMessage={tickerMessage}
            onExternalMessageHandled={handleTickerMessageHandled}
          />
        </div>

        {/* Sidebar (visible on larger screens) */}
        <aside className="hidden lg:flex lg:flex-col w-72 border-l border-terminal-border bg-terminal-surface">
          {/* Sessions */}
          <div className="p-4 border-b border-terminal-border">
            <SessionsList
              currentSessionId={activeSessionId}
              onSessionSelect={handleSessionSelect}
              onNewSession={handleNewSession}
              refreshTrigger={sessionRefreshTrigger}
            />
          </div>

          {/* Suggestions */}
          <div className="flex-1 overflow-y-auto p-4">
            <h2 className="text-sm font-semibold text-terminal-muted mb-3 uppercase tracking-wider">
              Try Asking
            </h2>
            <div className="space-y-2">
              {PROMPT_SUGGESTIONS.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => handlePromptClick(prompt)}
                  className="w-full text-left text-sm text-terminal-text hover:text-terminal-accent 
                           bg-terminal-bg hover:bg-terminal-border/50 
                           px-3 py-2 rounded transition-all duration-200"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Quick stats */}
          <div className="p-4 border-t border-terminal-border">
            <h2 className="text-sm font-semibold text-terminal-muted mb-3 uppercase tracking-wider">
              Available Tools
            </h2>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-terminal-bg px-2 py-1 rounded">
                <span className="text-terminal-accent">19</span> Free
              </div>
              <div className="bg-terminal-bg px-2 py-1 rounded">
                <span className="text-terminal-warning">5</span> Coming
              </div>
            </div>
            <a 
              href="/tools" 
              className="block mt-3 text-xs text-terminal-muted hover:text-terminal-accent"
            >
              View all tools →
            </a>
          </div>
        </aside>
      </main>

      {/* Footer */}
      <footer className="border-t border-terminal-border px-4 py-2 bg-terminal-surface">
        <div className="flex items-center justify-between text-xs text-terminal-muted">
          <span>100% Free • No limits • All tools included</span>
          <div className="flex items-center gap-4">
            <a href="/tools" className="hover:text-terminal-accent">Tools</a>
            <a href="https://twitter.com/johnnybets" className="hover:text-terminal-accent">@johnnybets</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function HomeLoading() {
  return (
    <div className="flex flex-col h-screen bg-terminal-bg">
      <header className="border-b border-terminal-border bg-terminal-surface px-4 py-3">
        <div className="h-6 w-32 bg-terminal-border/50 rounded animate-pulse"></div>
      </header>
      <main className="flex-1 flex items-center justify-center">
        <div className="text-terminal-muted">Loading...</div>
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<HomeLoading />}>
      <HomeContent />
    </Suspense>
  );
}
