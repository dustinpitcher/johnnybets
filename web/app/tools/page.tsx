'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import ToolCard from '@/components/ToolCard';
import { getTools, getToolStats, voteForTool, type Tool, type ToolStats } from '@/lib/api';

type FilterStatus = 'all' | 'free' | 'premium' | 'roadmap' | 'idea';
type FilterSport = 'all' | 'nfl' | 'nba' | 'nhl' | 'mlb';

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [stats, setStats] = useState<ToolStats | null>(null);
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [sportFilter, setSportFilter] = useState<FilterSport>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTools = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const filters: Record<string, string> = {};
      if (statusFilter !== 'all') filters.status = statusFilter;
      if (sportFilter !== 'all') filters.sport = sportFilter;

      const [toolsData, statsData] = await Promise.all([
        getTools(filters),
        getToolStats(),
      ]);

      setTools(toolsData.tools);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to fetch tools:', err);
      setError('Failed to load tools. API may be offline.');
      
      // Use mock data for demo
      setTools(MOCK_TOOLS);
      setStats(MOCK_STATS);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, sportFilter]);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  const handleVote = async (toolId: string) => {
    try {
      const result = await voteForTool(toolId);
      if (result.success) {
        setTools(prev =>
          prev.map(t =>
            t.id === toolId ? { ...t, votes: result.new_vote_count } : t
          )
        );
      }
    } catch (err) {
      console.error('Failed to vote:', err);
    }
  };

  // Group tools by status for display
  const freeTools = tools.filter(t => t.status === 'free');
  const roadmapTools = tools.filter(t => t.status === 'roadmap');
  const ideaTools = tools.filter(t => t.status === 'idea');

  return (
    <div className="min-h-screen bg-terminal-bg">
      {/* Header */}
      <header className="border-b border-terminal-border bg-terminal-surface">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-xl font-bold text-terminal-accent glow-green">
                JohnnyBets
              </Link>
              <span className="text-terminal-muted">/</span>
              <h1 className="text-lg font-semibold text-terminal-text">Tools</h1>
            </div>
            <Link href="/" className="btn btn-secondary text-sm">
              ← Back to Chat
            </Link>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats bar */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
              <div className="text-2xl font-bold text-terminal-accent">{stats.by_status.free}</div>
              <div className="text-sm text-terminal-muted">Free Tools</div>
            </div>
            <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
              <div className="text-2xl font-bold text-terminal-warning">{stats.by_status.roadmap}</div>
              <div className="text-sm text-terminal-muted">Coming Soon</div>
            </div>
            <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
              <div className="text-2xl font-bold text-terminal-info">{stats.by_status.idea}</div>
              <div className="text-sm text-terminal-muted">Ideas to Vote</div>
            </div>
            <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
              <div className="text-2xl font-bold text-terminal-text">{stats.total}</div>
              <div className="text-sm text-terminal-muted">Total Tools</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-8">
          <div className="flex items-center gap-2">
            <span className="text-sm text-terminal-muted">Status:</span>
            <div className="flex gap-1">
              {(['all', 'free', 'roadmap', 'idea'] as FilterStatus[]).map(status => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`px-3 py-1 rounded text-sm transition-colors ${
                    statusFilter === status
                      ? 'bg-terminal-accent text-terminal-bg'
                      : 'bg-terminal-surface text-terminal-muted hover:text-terminal-text'
                  }`}
                >
                  {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-terminal-muted">Sport:</span>
            <div className="flex gap-1">
              {(['all', 'nfl', 'nba', 'nhl', 'mlb'] as FilterSport[]).map(sport => (
                <button
                  key={sport}
                  onClick={() => setSportFilter(sport)}
                  className={`px-3 py-1 rounded text-sm transition-colors ${
                    sportFilter === sport
                      ? 'bg-terminal-accent text-terminal-bg'
                      : 'bg-terminal-surface text-terminal-muted hover:text-terminal-text'
                  }`}
                >
                  {sport.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="bg-terminal-error/10 border border-terminal-error/30 rounded-lg p-4 mb-8">
            <p className="text-terminal-error">{error}</p>
            <p className="text-sm text-terminal-muted mt-1">Showing demo data.</p>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-terminal-muted loading-dots">Loading tools</div>
          </div>
        )}

        {/* Tools grid */}
        {!isLoading && (
          <div className="space-y-12">
            {/* Free Tools */}
            {freeTools.length > 0 && (statusFilter === 'all' || statusFilter === 'free') && (
              <section>
                <h2 className="text-lg font-semibold text-terminal-accent mb-4 flex items-center gap-2">
                  <span className="text-green-500">●</span>
                  Available Now
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {freeTools.map(tool => (
                    <ToolCard key={tool.id} tool={tool} />
                  ))}
                </div>
              </section>
            )}

            {/* Roadmap Tools */}
            {roadmapTools.length > 0 && (statusFilter === 'all' || statusFilter === 'roadmap') && (
              <section>
                <h2 className="text-lg font-semibold text-terminal-warning mb-4 flex items-center gap-2">
                  <span className="text-amber-500">●</span>
                  Coming Soon
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {roadmapTools.map(tool => (
                    <ToolCard key={tool.id} tool={tool} />
                  ))}
                </div>
              </section>
            )}

            {/* Idea Tools */}
            {ideaTools.length > 0 && (statusFilter === 'all' || statusFilter === 'idea') && (
              <section>
                <h2 className="text-lg font-semibold text-terminal-muted mb-4 flex items-center gap-2">
                  <span className="text-gray-500">●</span>
                  Ideas - Vote for your favorites!
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {ideaTools.map(tool => (
                    <ToolCard key={tool.id} tool={tool} onVote={handleVote} />
                  ))}
                </div>
              </section>
            )}

            {/* Empty state */}
            {tools.length === 0 && !isLoading && (
              <div className="text-center py-12">
                <p className="text-terminal-muted">No tools match your filters.</p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-terminal-border px-4 py-6 mt-12">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-sm text-terminal-muted">
            All free tools are available now. Premium tools coming soon.
          </p>
          <p className="text-xs text-terminal-muted mt-2">
            Have an idea for a new tool? <a href="#" className="text-terminal-accent hover:underline">Let us know!</a>
          </p>
        </div>
      </footer>
    </div>
  );
}

// Mock data for demo when API is unavailable
const MOCK_TOOLS: Tool[] = [
  {
    id: 'fetch_sportsbook_odds',
    name: 'Live Odds',
    description: 'Real-time odds from 10+ sportsbooks including DraftKings, FanDuel, BetMGM, and more.',
    category: 'general',
    status: 'free',
    icon: 'chart-line',
    sports: ['nfl', 'nhl', 'mlb', 'nba'],
    votes: 0,
  },
  {
    id: 'analyze_player_props',
    name: 'Prop Alpha',
    description: 'Contextual player prop analysis with defense profiling and weather adjustments.',
    category: 'nfl',
    status: 'free',
    icon: 'user-chart',
    sports: ['nfl'],
    votes: 0,
  },
  {
    id: 'analyze_goalie_props',
    name: 'Goalie Alpha',
    description: 'NHL goalie prop analysis with B2B splits and xGSV%.',
    category: 'nhl',
    status: 'free',
    icon: 'hockey-puck',
    sports: ['nhl'],
    votes: 0,
  },
  {
    id: 'find_arbitrage_opportunities',
    name: 'Arbitrage Scanner',
    description: 'Find guaranteed profit opportunities across sportsbooks.',
    category: 'general',
    status: 'free',
    icon: 'magnifying-glass-dollar',
    sports: ['nfl', 'nhl', 'mlb'],
    votes: 0,
  },
  {
    id: 'sharps_consensus',
    name: 'Sharps Consensus',
    description: 'Aggregated sharp bettor positions and professional money flow.',
    category: 'general',
    status: 'roadmap',
    icon: 'brain',
    sports: ['nfl', 'nhl', 'mlb'],
    eta: 'Q2 2026',
    votes: 0,
  },
  {
    id: 'steam_move_detector',
    name: 'Steam Move Detector',
    description: 'Detect coordinated sharp betting action across sportsbooks.',
    category: 'general',
    status: 'idea',
    icon: 'fire',
    sports: ['nfl', 'nhl', 'mlb'],
    votes: 12,
  },
];

const MOCK_STATS: ToolStats = {
  total: 32,
  by_status: { free: 28, premium: 0, roadmap: 2, idea: 2 },
  by_category: { general: 12, nfl: 4, nba: 5, nhl: 5, mlb: 6 },
  by_sport: { nfl: 16, nhl: 16, mlb: 17, nba: 13 },
};

