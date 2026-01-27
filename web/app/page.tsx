'use client';

import { useState, useCallback, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Terminal from '@/components/Terminal';
import Ticker from '@/components/Ticker';
import UserMenu from '@/components/UserMenu';
import SessionsList from '@/components/SessionsList';

// Prompt suggestions based on upcoming games
const PROMPT_SUGGESTIONS = [
  "Break down Patriots vs Seahawks for Super Bowl LX",
  "Best player props for the Super Bowl this Sunday",
  "Find arbitrage opportunities in tonight's NBA games",
  "Which NHL goalies have the best save props tonight?",
  "What's the sharp money saying about the Super Bowl?",
  "Compare Super Bowl MVP odds for Mac Jones vs Sam Darnold",
];

function HomeContent() {
  const searchParams = useSearchParams();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [externalMessage, setExternalMessage] = useState<string | null>(null);
  const [populateMessage, setPopulateMessage] = useState<string | null>(null);
  const [sessionRefreshTrigger, setSessionRefreshTrigger] = useState(0);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Load session from URL query parameter
  useEffect(() => {
    const sessionFromUrl = searchParams.get('session');
    if (sessionFromUrl) {
      setActiveSessionId(sessionFromUrl);
    }
  }, [searchParams]);

  // Ticker click: populate input only (user must press Enter)
  const handleGameClick = useCallback((game: any, prompt: string) => {
    setPopulateMessage(prompt);
  }, []);

  const handlePopulateHandled = useCallback(() => {
    setPopulateMessage(null);
  }, []);

  const handleExternalMessageHandled = useCallback(() => {
    setExternalMessage(null);
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
    setIsMobileSidebarOpen(false); // Close mobile sidebar on selection
  }, []);

  // Prompt suggestion click: auto-submit
  const handlePromptClick = (prompt: string) => {
    // Start a new session with this prompt
    setActiveSessionId(null);
    // Use external message to auto-submit
    setExternalMessage(prompt);
    setIsMobileSidebarOpen(false); // Close mobile sidebar
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
            <UserMenu />
            {/* Mobile sidebar toggle */}
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="lg:hidden p-2 text-terminal-muted hover:text-terminal-accent transition-colors"
              aria-label="Open menu"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-6 h-6"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>
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
            externalMessage={externalMessage}
            onExternalMessageHandled={handleExternalMessageHandled}
            populateMessage={populateMessage}
            onPopulateHandled={handlePopulateHandled}
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

        {/* Mobile Sidebar Flyout */}
        <div 
          className={`lg:hidden fixed inset-0 z-50 transition-opacity duration-300 ${
            isMobileSidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
        >
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setIsMobileSidebarOpen(false)}
          />
          
          {/* Drawer */}
          <aside 
            className={`absolute top-0 right-0 h-full w-80 max-w-[85vw] bg-terminal-surface border-l border-terminal-border flex flex-col transform transition-transform duration-300 ease-out ${
              isMobileSidebarOpen ? 'translate-x-0' : 'translate-x-full'
            }`}
          >
            {/* Header with close button */}
            <div className="flex items-center justify-between p-4 border-b border-terminal-border">
              <h2 className="text-sm font-semibold text-terminal-accent uppercase tracking-wider">
                Menu
              </h2>
              <button
                onClick={() => setIsMobileSidebarOpen(false)}
                className="p-2 text-terminal-muted hover:text-terminal-accent transition-colors"
                aria-label="Close menu"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="w-6 h-6"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Sessions */}
            <div className="p-4 border-b border-terminal-border">
              <SessionsList
                currentSessionId={activeSessionId}
                onSessionSelect={handleSessionSelect}
                onNewSession={() => {
                  handleNewSession();
                  setIsMobileSidebarOpen(false);
                }}
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
                onClick={() => setIsMobileSidebarOpen(false)}
              >
                View all tools →
              </a>
            </div>
          </aside>
        </div>
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
