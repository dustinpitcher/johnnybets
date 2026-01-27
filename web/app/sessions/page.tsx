'use client';

import { useSession } from 'next-auth/react';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { getSessions, deleteSession, ChatSession } from '@/lib/sessions';

export default function SessionsPage() {
  const { status: authStatus } = useSession();
  const isAuthenticated = authStatus === 'authenticated';
  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load sessions
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
    if (authStatus !== 'loading') {
      loadSessions();
    }
  }, [loadSessions, authStatus]);

  const handleDelete = async (sessionId: string) => {
    if (confirm('Delete this session?')) {
      await deleteSession(sessionId, isAuthenticated);
      await loadSessions();
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-terminal-bg">
      {/* Header */}
      <header className="border-b border-terminal-border bg-terminal-surface">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold text-terminal-accent glow-green">
              JohnnyBets
            </Link>
            <span className="text-terminal-muted">/</span>
            <h1 className="text-lg text-terminal-text">My Sessions</h1>
          </div>
          <Link 
            href="/"
            className="btn btn-ghost text-sm"
          >
            ← Back to Chat
          </Link>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-terminal-muted">Loading sessions...</div>
          </div>
        ) : sessions.length === 0 ? (
          /* Empty state */
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📊</div>
            <h2 className="text-xl font-semibold text-terminal-text mb-2">
              No sessions yet
            </h2>
            <p className="text-terminal-muted mb-6 max-w-md mx-auto">
              Start a new betting analysis session and it will appear here. 
              {isAuthenticated 
                ? ' Your sessions are synced to your account.'
                : ' Sign in to sync sessions across devices.'}
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-6 py-3 bg-terminal-accent text-terminal-bg 
                       rounded-lg font-medium hover:bg-terminal-accent/80 transition-colors"
            >
              Start New Session
              <span>→</span>
            </Link>

            {/* Tips */}
            <div className="mt-12 grid gap-4 max-w-lg mx-auto text-left">
              <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
                <h3 className="text-sm font-medium text-terminal-accent mb-1">
                  💡 Pro tip
                </h3>
                <p className="text-sm text-terminal-muted">
                  Click any game in the ticker to start analyzing it instantly.
                </p>
              </div>
              <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
                <h3 className="text-sm font-medium text-terminal-accent mb-1">
                  🏷️ Session tags
                </h3>
                <p className="text-sm text-terminal-muted">
                  Teams and players you mention are automatically tagged for easy filtering.
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* Sessions list */
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-6">
              <p className="text-terminal-muted">
                {sessions.length} session{sessions.length !== 1 ? 's' : ''}
                {isAuthenticated && <span className="ml-2 text-terminal-accent">(synced)</span>}
              </p>
              <Link
                href="/"
                className="text-sm text-terminal-accent hover:underline"
              >
                + New Session
              </Link>
            </div>

            {sessions.map((chatSession) => (
              <div
                key={chatSession.id}
                className="bg-terminal-surface border border-terminal-border rounded-lg p-4
                         hover:border-terminal-accent/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <Link
                    href={`/?session=${chatSession.id}`}
                    className="flex-1 min-w-0"
                  >
                    <h3 className="font-medium text-terminal-text mb-1 hover:text-terminal-accent">
                      {chatSession.title}
                    </h3>
                    <p className="text-sm text-terminal-muted">
                      {chatSession.messages.length} messages • {formatDate(chatSession.updatedAt)}
                    </p>
                  </Link>
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/?session=${chatSession.id}`}
                      className="text-xs text-terminal-muted hover:text-terminal-accent px-2 py-1"
                    >
                      Open →
                    </Link>
                    <button
                      onClick={() => handleDelete(chatSession.id)}
                      className="text-xs text-terminal-muted hover:text-terminal-error px-2 py-1"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                {chatSession.tags.length > 0 && (
                  <div className="flex gap-2 mt-3">
                    {chatSession.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs px-2 py-1 bg-terminal-bg rounded text-terminal-muted"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
