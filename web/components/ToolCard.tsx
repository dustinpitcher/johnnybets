'use client';

import React from 'react';
import type { Tool } from '@/lib/api';

// Icon mapping (using simple emoji for now, can replace with heroicons)
const ICON_MAP: Record<string, string> = {
  'chart-line': '📊',
  'crystal-ball': '🔮',
  'magnifying-glass-dollar': '🔍',
  'twitter': '𝕏',
  'bandage': '🩹',
  'trending-up': '📈',
  'newspaper': '📰',
  'shield-check': '🛡️',
  'floppy-disk': '💾',
  'file-text': '📄',
  'user-chart': '👤',
  'shield': '🛡️',
  'cloud-sun': '⛅',
  'chart-bar': '📊',
  'hockey-puck': '🏒',
  'user-shield': '🧤',
  'users': '👥',
  'swords': '⚔️',
  'whistle': '🎯',
  'baseball': '⚾',
  'stadium': '🏟️',
  'users-gear': '⚙️',
  'brain': '🧠',
  'bell': '🔔',
  'fire': '🔥',
  'target': '🎯',
};

function getStatusBadge(status: string): React.ReactNode {
  switch (status) {
    case 'free':
      return <span className="badge badge-free">Free</span>;
    case 'premium':
      return <span className="badge badge-premium">Premium</span>;
    case 'roadmap':
      return <span className="badge badge-roadmap">Coming Soon</span>;
    case 'idea':
      return <span className="badge badge-idea">Vote</span>;
    default:
      return null;
  }
}

function getSportBadge(sport: string): React.ReactNode {
  switch (sport) {
    case 'nfl':
      return <span className="sport-nfl text-xs px-1.5 py-0.5 rounded">NFL</span>;
    case 'nhl':
      return <span className="sport-nhl text-xs px-1.5 py-0.5 rounded">NHL</span>;
    case 'mlb':
      return <span className="sport-mlb text-xs px-1.5 py-0.5 rounded">MLB</span>;
    case 'nba':
      return <span className="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-500/30">NBA</span>;
    default:
      return null;
  }
}

interface ToolCardProps {
  tool: Tool;
  onVote?: (toolId: string) => void;
}

export default function ToolCard({ tool, onVote }: ToolCardProps) {
  const icon = ICON_MAP[tool.icon] || '🔧';
  const isAvailable = tool.status === 'free';
  const isVoteable = tool.status === 'idea';

  return (
    <div 
      className={`
        bg-terminal-surface border border-terminal-border rounded-lg p-4
        transition-all duration-200 hover:border-terminal-accent/50
        ${!isAvailable ? 'opacity-75' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h3 className="font-semibold text-terminal-text">{tool.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              {getStatusBadge(tool.status)}
              {tool.eta && (
                <span className="text-xs text-terminal-muted">{tool.eta}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-terminal-muted mb-4 line-clamp-2">
        {tool.description}
      </p>

      {/* Sports */}
      <div className="flex items-center gap-2 mb-4">
        {tool.sports.map(sport => (
          <React.Fragment key={sport}>
            {getSportBadge(sport)}
          </React.Fragment>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-terminal-border">
        <span className="text-xs text-terminal-muted capitalize">
          {tool.category}
        </span>
        
        {isVoteable && onVote && (
          <button
            onClick={() => onVote(tool.id)}
            className="flex items-center gap-1 text-sm text-terminal-muted hover:text-terminal-accent transition-colors"
          >
            <span>👍</span>
            <span>{tool.votes}</span>
          </button>
        )}
        
        {isAvailable && (
          <span className="text-xs text-terminal-accent">Available now</span>
        )}
      </div>
    </div>
  );
}

