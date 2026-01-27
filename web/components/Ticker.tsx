'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';

interface Game {
  id: string;
  sport: 'nfl' | 'nhl' | 'mlb' | 'nba';
  homeTeam: string;
  awayTeam: string;
  homeScore?: number;
  awayScore?: number;
  status: 'scheduled' | 'live' | 'final';
  startTime?: string;
  period?: string;
  broadcast?: string;
}

interface ScoresResponse {
  games: Game[];
  updated_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

function getSportColor(sport: string): string {
  switch (sport) {
    case 'nfl':
      return 'text-blue-400';
    case 'nhl':
      return 'text-red-400';
    case 'mlb':
      return 'text-green-400';
    case 'nba':
      return 'text-orange-400';
    default:
      return 'text-terminal-muted';
  }
}

function getStatusBadge(game: Game): React.ReactNode {
  if (game.status === 'live') {
    return (
      <span className="inline-flex items-center gap-1 text-red-500 text-xs">
        <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
        {game.period || 'LIVE'}
      </span>
    );
  }
  if (game.status === 'final') {
    return <span className="text-terminal-muted text-xs">FINAL</span>;
  }
  return <span className="text-terminal-muted text-xs">{game.startTime}</span>;
}

interface TickerProps {
  className?: string;
  refreshInterval?: number; // in milliseconds
  onGameClick?: (game: Game, prompt: string) => void;
}

export default function Ticker({ className, refreshInterval = 60000, onGameClick }: TickerProps) {
  const [games, setGames] = useState<Game[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Touch/swipe handling
  const [touchStartX, setTouchStartX] = useState<number | null>(null);
  const [touchOffset, setTouchOffset] = useState(0);
  const [isSwiping, setIsSwiping] = useState(false);
  const tickerRef = useRef<HTMLDivElement>(null);

  const fetchScores = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/scores`);
      if (!response.ok) {
        throw new Error('Failed to fetch scores');
      }
      const data: ScoresResponse = await response.json();
      setGames(data.games);
      setLastUpdated(data.updated_at);
      setError(null);
    } catch (err) {
      console.error('Error fetching scores:', err);
      setError('Unable to load scores');
      // Keep existing games on error
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchScores();
  }, [fetchScores]);

  // Polling for updates
  useEffect(() => {
    const interval = setInterval(fetchScores, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchScores, refreshInterval]);

  // Touch event handlers for mobile swipe
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    setTouchStartX(e.touches[0].clientX);
    setIsSwiping(true);
    setIsPaused(true);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (touchStartX !== null && isSwiping) {
      const currentX = e.touches[0].clientX;
      const delta = currentX - touchStartX;
      setTouchOffset(prev => prev + delta);
      setTouchStartX(currentX);
    }
  }, [touchStartX, isSwiping]);

  const handleTouchEnd = useCallback(() => {
    setTouchStartX(null);
    setIsSwiping(false);
    // Resume animation after a brief moment
    setTimeout(() => {
      setIsPaused(false);
      setTouchOffset(0);
    }, 100);
  }, []);

  // Don't render if no games and still loading
  if (isLoading && games.length === 0) {
    return (
      <div className={`bg-terminal-bg border-b border-terminal-border py-2 px-4 ${className}`}>
        <span className="text-terminal-muted text-sm">Loading scores...</span>
      </div>
    );
  }

  // Show error state but keep ticker visible if we have cached games
  if (error && games.length === 0) {
    return (
      <div className={`bg-terminal-bg border-b border-terminal-border py-2 px-4 ${className}`}>
        <span className="text-terminal-muted text-sm">{error}</span>
      </div>
    );
  }

  if (games.length === 0) {
    return (
      <div className={`bg-terminal-bg border-b border-terminal-border py-2 px-4 ${className}`}>
        <span className="text-terminal-muted text-sm">No games scheduled</span>
      </div>
    );
  }

  return (
    <div 
      className={`bg-terminal-bg border-b border-terminal-border overflow-hidden ${className}`}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      <div 
        ref={tickerRef}
        className="flex items-center gap-6 py-2 px-4"
        style={{
          animation: 'marquee var(--marquee-duration) linear infinite',
          animationPlayState: isPaused ? 'paused' : 'running',
          transform: isSwiping ? `translateX(${touchOffset}px)` : undefined,
        }}
      >
        {/* Duplicate games for seamless loop */}
        {[...games, ...games].map((game, index) => (
          <button
            key={`${game.id}-${index}`}
            className="flex items-center gap-3 whitespace-nowrap hover:bg-terminal-surface px-2 py-1 rounded transition-colors"
            onClick={() => {
              // Generate a contextual prompt based on game status
              let prompt: string;
              if (game.status === 'live') {
                prompt = `The ${game.awayTeam} vs ${game.homeTeam} game is live (${game.awayScore}-${game.homeScore}). What's the current betting situation and any live opportunities?`;
              } else if (game.status === 'final') {
                prompt = `The ${game.awayTeam} @ ${game.homeTeam} game just ended ${game.awayScore}-${game.homeScore}. Any insights on how this affects upcoming bets or futures?`;
              } else {
                prompt = `Analyze the upcoming ${game.awayTeam} @ ${game.homeTeam} ${game.sport.toUpperCase()} game. What are the best betting opportunities?`;
              }
              onGameClick?.(game, prompt);
            }}
          >
            {/* Sport indicator */}
            <span className={`text-xs font-bold uppercase ${getSportColor(game.sport)}`}>
              {game.sport}
            </span>
            
            {/* Teams and score */}
            <div className="flex items-center gap-2">
              <span className="text-terminal-text font-medium">
                {game.awayTeam}
              </span>
              
              {game.status !== 'scheduled' ? (
                <>
                  <span className={`text-terminal-text font-bold ${
                    game.awayScore !== undefined && game.homeScore !== undefined && 
                    game.awayScore > game.homeScore ? 'text-terminal-accent' : ''
                  }`}>
                    {game.awayScore}
                  </span>
                  <span className="text-terminal-muted">-</span>
                  <span className={`text-terminal-text font-bold ${
                    game.awayScore !== undefined && game.homeScore !== undefined && 
                    game.homeScore > game.awayScore ? 'text-terminal-accent' : ''
                  }`}>
                    {game.homeScore}
                  </span>
                </>
              ) : (
                <span className="text-terminal-muted">@</span>
              )}
              
              <span className="text-terminal-text font-medium">
                {game.homeTeam}
              </span>
            </div>
            
            {/* Status */}
            <div className="flex items-center gap-1">
              {getStatusBadge(game)}
            </div>

            {/* Broadcast (optional) */}
            {game.broadcast && (
              <span className="text-terminal-muted text-xs">
                {game.broadcast}
              </span>
            )}
          </button>
        ))}
      </div>

      <style jsx>{`
        @keyframes marquee {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
        
        /* Default (mobile-first): faster animation */
        div {
          --marquee-duration: 12s;
        }
        
        /* Desktop: slower, more relaxed animation */
        @media (min-width: 768px) {
          div {
            --marquee-duration: 24s;
          }
        }
      `}</style>
    </div>
  );
}
