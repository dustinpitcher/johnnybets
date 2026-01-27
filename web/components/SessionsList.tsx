'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { getSessions, deleteSession, ChatSession } from '@/lib/sessions';

interface SessionsListProps {
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string | null) => void;
  onNewSession: () => void;
  refreshTrigger?: number; // Increment to trigger refresh
}

export default function SessionsList({ 
  currentSessionId, 
  onSessionSelect, 
  onNewSession,
  refreshTrigger = 0,
}: SessionsListProps) {
  const { status: authStatus } = useSession();
  const isAuthenticated = authStatus === 'authenticated';
  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // Load sessions on mount and when refreshTrigger or auth changes
  const loadSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const loadedSessions = await getSessions(isAuthenticated);
      setSessions(loadedSessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions, refreshTrigger]);

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (confirm('Delete this session?')) {
      await deleteSession(sessionId, isAuthenticated);
      await loadSessions();
      if (currentSessionId === sessionId) {
        onSessionSelect(null);
      }
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 text-sm font-semibold text-terminal-muted uppercase tracking-wider hover:text-terminal-text"
        >
          <span className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
          Sessions
          {sessions.length > 0 && (
            <span className="text-xs font-normal">({sessions.length})</span>
          )}
          {isLoading && (
            <span className="ml-1 w-2 h-2 bg-terminal-accent rounded-full animate-pulse" />
          )}
        </button>
        <button
          onClick={onNewSession}
          className="text-xs text-terminal-accent hover:underline"
          title="New session"
        >
          + New
        </button>
      </div>

      {/* Sessions list */}
      {isExpanded && (
        <div className="space-y-1">
          {sessions.length === 0 ? (
            <p className="text-xs text-terminal-muted py-2">
              {isLoading ? 'Loading...' : 'No sessions yet. Start chatting to create one.'}
            </p>
          ) : (
            sessions.slice(0, 10).map((session) => (
              <div
                key={session.id}
                onClick={() => onSessionSelect(session.id)}
                className={`
                  group flex items-start justify-between gap-2 px-2 py-1.5 rounded cursor-pointer
                  text-sm transition-colors
                  ${currentSessionId === session.id 
                    ? 'bg-terminal-accent/20 text-terminal-accent' 
                    : 'text-terminal-text hover:bg-terminal-bg'}
                `}
              >
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm">
                    {session.title}
                  </p>
                  <p className="text-xs text-terminal-muted">
                    {formatDate(session.updatedAt)}
                    {session.messages.length > 0 && (
                      <span> • {session.messages.length} msgs</span>
                    )}
                  </p>
                </div>
                <button
                  onClick={(e) => handleDelete(e, session.id)}
                  className="opacity-0 group-hover:opacity-100 text-terminal-muted hover:text-terminal-error 
                           transition-opacity px-1"
                  title="Delete session"
                >
                  ×
                </button>
              </div>
            ))
          )}
          
          {sessions.length > 10 && (
            <a 
              href="/sessions" 
              className="block text-xs text-terminal-muted hover:text-terminal-accent py-1 px-2"
            >
              View all {sessions.length} sessions →
            </a>
          )}
        </div>
      )}
    </div>
  );
}
