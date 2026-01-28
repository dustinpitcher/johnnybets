'use client';

import { useState, useEffect, useCallback } from 'react';

// Types for feedback data
interface ContextMessage {
  role: string;
  content: string;
  toolsUsed: string[];
  timestamp: string;
}

interface ContextSnapshot {
  recentMessages: ContextMessage[];
  sessionMeta: {
    model: string | null;
    reasoning: string | null;
    entities: unknown;
    title: string | null;
    createdAt: string;
  };
  userMeta: {
    isAuthenticated: boolean;
    hasApiKeys: boolean;
  };
}

interface FeedbackItem {
  id: string;
  type: 'up' | 'down';
  comment: string | null;
  messageContent: string | null;
  sessionId: string | null;
  contextSnapshot?: ContextSnapshot | null;
  createdAt: string;
}

interface FeedbackStats {
  totalUp: number;
  totalDown: number;
  total: number;
  positiveRate: number;
}

interface FeedbackResponse {
  stats: FeedbackStats;
  feedback: FeedbackItem[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    hasMore: boolean;
  };
  isAdmin: boolean;
}

export default function AdminFeedbackPage() {
  const [feedbackData, setFeedbackData] = useState<FeedbackResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<'all' | 'up' | 'down'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedContext, setExpandedContext] = useState<ContextSnapshot | null>(null);
  const [loadingContext, setLoadingContext] = useState(false);

  const fetchFeedback = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        limit: '50',
        offset: '0',
        includeContext: 'false', // Don't include context in list view for performance
      });
      
      if (typeFilter !== 'all') {
        params.set('type', typeFilter);
      }

      const res = await fetch(`/api/feedback?${params}`);
      if (!res.ok) {
        throw new Error('Failed to fetch feedback');
      }

      const data = await res.json();
      setFeedbackData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [typeFilter]);

  useEffect(() => {
    fetchFeedback();
  }, [fetchFeedback]);

  const handleExpand = async (feedback: FeedbackItem) => {
    if (expandedId === feedback.id) {
      // Collapse
      setExpandedId(null);
      setExpandedContext(null);
      return;
    }

    setExpandedId(feedback.id);
    setLoadingContext(true);
    setExpandedContext(null);

    try {
      // Fetch full feedback with context
      const res = await fetch(`/api/feedback/${feedback.id}`);
      if (res.ok) {
        const data = await res.json();
        setExpandedContext(data.contextSnapshot || null);
      }
    } catch (err) {
      console.error('Failed to fetch context:', err);
    } finally {
      setLoadingContext(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      return `${diffMins} min ago`;
    }
    if (diffHours < 24) {
      return `${diffHours}h ago`;
    }
    if (diffDays < 7) {
      return `${diffDays}d ago`;
    }
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-mono font-bold text-terminal-text">
          Feedback Review
        </h1>
        <button
          onClick={() => fetchFeedback()}
          className="px-3 py-1.5 text-sm font-mono text-terminal-muted hover:text-terminal-accent 
                   border border-terminal-border hover:border-terminal-accent rounded transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Stats */}
      {feedbackData && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
            <div className="text-2xl font-mono font-bold text-terminal-text">
              {feedbackData.stats.total}
            </div>
            <div className="text-sm text-terminal-muted">Total Feedback</div>
          </div>
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
            <div className="text-2xl font-mono font-bold text-terminal-accent">
              {feedbackData.stats.totalUp}
            </div>
            <div className="text-sm text-terminal-muted">Positive</div>
          </div>
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
            <div className="text-2xl font-mono font-bold text-red-500">
              {feedbackData.stats.totalDown}
            </div>
            <div className="text-sm text-terminal-muted">Negative</div>
          </div>
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
            <div className="text-2xl font-mono font-bold text-terminal-text">
              {feedbackData.stats.positiveRate}%
            </div>
            <div className="text-sm text-terminal-muted">Positive Rate</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <span className="text-sm text-terminal-muted">Filter:</span>
        <div className="flex gap-2">
          {(['all', 'up', 'down'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setTypeFilter(filter)}
              className={`px-3 py-1 text-sm font-mono rounded transition-colors ${
                typeFilter === filter
                  ? 'bg-terminal-accent text-terminal-bg'
                  : 'text-terminal-muted hover:text-terminal-text border border-terminal-border'
              }`}
            >
              {filter === 'all' ? 'All' : filter === 'up' ? 'Positive' : 'Negative'}
            </button>
          ))}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500 rounded-lg p-4 text-red-500">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-terminal-muted">Loading feedback...</div>
        </div>
      )}

      {/* Feedback List */}
      {!loading && feedbackData && (
        <div className="space-y-3">
          {feedbackData.feedback.length === 0 ? (
            <div className="text-center py-12 text-terminal-muted">
              No feedback found.
            </div>
          ) : (
            feedbackData.feedback.map((item) => (
              <div
                key={item.id}
                className="bg-terminal-surface border border-terminal-border rounded-lg overflow-hidden"
              >
                {/* Feedback Header */}
                <button
                  onClick={() => handleExpand(item)}
                  className="w-full px-4 py-3 flex items-start justify-between text-left hover:bg-terminal-bg/50 transition-colors"
                >
                  <div className="flex items-start gap-3 flex-1">
                    {/* Type Badge */}
                    <span
                      className={`px-2 py-0.5 text-xs font-mono rounded ${
                        item.type === 'up'
                          ? 'bg-terminal-accent/20 text-terminal-accent'
                          : 'bg-red-500/20 text-red-500'
                      }`}
                    >
                      {item.type === 'up' ? 'UP' : 'DOWN'}
                    </span>

                    <div className="flex-1 min-w-0">
                      {/* Comment */}
                      {item.comment ? (
                        <p className="text-terminal-text text-sm">
                          &quot;{item.comment}&quot;
                        </p>
                      ) : (
                        <p className="text-terminal-muted text-sm italic">
                          No comment provided
                        </p>
                      )}

                      {/* Message preview */}
                      {item.messageContent && (
                        <p className="text-terminal-muted text-xs mt-1 truncate">
                          Re: {item.messageContent.slice(0, 100)}...
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-xs text-terminal-muted">
                      {formatDate(item.createdAt)}
                    </span>
                    <svg
                      className={`w-4 h-4 text-terminal-muted transition-transform ${
                        expandedId === item.id ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </button>

                {/* Expanded Context */}
                {expandedId === item.id && (
                  <div className="border-t border-terminal-border px-4 py-4 bg-terminal-bg/50">
                    {loadingContext ? (
                      <div className="text-terminal-muted text-sm">
                        Loading context...
                      </div>
                    ) : expandedContext ? (
                      <div className="space-y-4">
                        {/* Session Metadata */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-terminal-muted">Model:</span>{' '}
                            <span className="text-terminal-text font-mono">
                              {expandedContext.sessionMeta.model || 'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-terminal-muted">Reasoning:</span>{' '}
                            <span className="text-terminal-text font-mono">
                              {expandedContext.sessionMeta.reasoning || 'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-terminal-muted">Authenticated:</span>{' '}
                            <span className="text-terminal-text">
                              {expandedContext.userMeta.isAuthenticated ? 'Yes' : 'No'}
                            </span>
                          </div>
                          <div>
                            <span className="text-terminal-muted">Has API Keys:</span>{' '}
                            <span className="text-terminal-text">
                              {expandedContext.userMeta.hasApiKeys ? 'Yes' : 'No'}
                            </span>
                          </div>
                        </div>

                        {/* Session Title */}
                        {expandedContext.sessionMeta.title && (
                          <div className="text-sm">
                            <span className="text-terminal-muted">Session:</span>{' '}
                            <span className="text-terminal-text">
                              {expandedContext.sessionMeta.title}
                            </span>
                          </div>
                        )}

                        {/* Recent Messages */}
                        <div>
                          <h4 className="text-sm font-mono text-terminal-muted mb-2">
                            Recent Messages ({expandedContext.recentMessages.length})
                          </h4>
                          <div className="space-y-2 max-h-96 overflow-y-auto">
                            {expandedContext.recentMessages.map((msg, idx) => (
                              <div
                                key={idx}
                                className={`p-3 rounded text-sm ${
                                  msg.role === 'user'
                                    ? 'bg-terminal-surface border-l-2 border-terminal-accent'
                                    : 'bg-terminal-bg border-l-2 border-terminal-muted'
                                }`}
                              >
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-mono text-xs text-terminal-muted uppercase">
                                    {msg.role}
                                  </span>
                                  {msg.toolsUsed.length > 0 && (
                                    <span className="text-xs text-terminal-accent">
                                      Tools: {msg.toolsUsed.join(', ')}
                                    </span>
                                  )}
                                </div>
                                <p className="text-terminal-text whitespace-pre-wrap break-words">
                                  {msg.content.length > 500
                                    ? msg.content.slice(0, 500) + '...'
                                    : msg.content}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-terminal-muted text-sm">
                        No context available for this feedback.
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Pagination Info */}
      {feedbackData?.pagination && (
        <div className="text-center text-sm text-terminal-muted">
          Showing {feedbackData.feedback.length} of {feedbackData.pagination.total} items
        </div>
      )}
    </div>
  );
}
