'use client';

import { useState, useEffect, useCallback } from 'react';

interface WaitlistEntry {
  id: string;
  email: string;
  source: string | null;
  invitedAt: string | null;
  createdAt: string;
}

interface WaitlistStats {
  pending: number;
  invited: number;
  total: number;
}

interface WaitlistResponse {
  entries: WaitlistEntry[];
  stats: WaitlistStats;
}

export default function AdminInvitesPage() {
  const [data, setData] = useState<WaitlistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'pending' | 'invited' | 'all'>('pending');
  const [sendingIds, setSendingIds] = useState<Set<string>>(new Set());
  const [successIds, setSuccessIds] = useState<Set<string>>(new Set());

  const fetchWaitlist = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        limit: '100',
        showInvited: filter === 'all' || filter === 'invited' ? 'true' : 'false',
      });

      const res = await fetch(`/api/admin/send-invite?${params}`);
      if (!res.ok) {
        throw new Error('Failed to fetch waitlist');
      }

      const json = await res.json();
      
      // Filter client-side for "invited" only view
      if (filter === 'invited') {
        json.entries = json.entries.filter((e: WaitlistEntry) => e.invitedAt);
      } else if (filter === 'pending') {
        json.entries = json.entries.filter((e: WaitlistEntry) => !e.invitedAt);
      }
      
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchWaitlist();
  }, [fetchWaitlist]);

  const sendInvite = async (entry: WaitlistEntry) => {
    setSendingIds((prev) => new Set(prev).add(entry.id));

    try {
      const res = await fetch('/api/admin/send-invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ waitlistEntryId: entry.id }),
      });

      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error || 'Failed to send invite');
      }

      // Mark as success
      setSuccessIds((prev) => new Set(prev).add(entry.id));
      
      // Refresh list after a moment
      setTimeout(() => {
        fetchWaitlist();
      }, 1500);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to send invite');
    } finally {
      setSendingIds((prev) => {
        const next = new Set(prev);
        next.delete(entry.id);
        return next;
      });
    }
  };

  const sendAllPending = async () => {
    if (!data?.entries) return;
    
    const pending = data.entries.filter((e) => !e.invitedAt);
    if (pending.length === 0) return;
    
    if (!confirm(`Send invites to all ${pending.length} pending entries?`)) {
      return;
    }

    for (const entry of pending) {
      await sendInvite(entry);
      // Small delay between sends to avoid rate limiting
      await new Promise((r) => setTimeout(r, 500));
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
      return `${diffMins}m ago`;
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
          Waitlist & Invites
        </h1>
        <div className="flex items-center gap-3">
          {filter === 'pending' && data && data.stats.pending > 0 && (
            <button
              onClick={sendAllPending}
              className="px-3 py-1.5 text-sm font-mono bg-terminal-accent text-terminal-bg 
                       rounded hover:opacity-90 transition-opacity"
            >
              Send All ({data.stats.pending})
            </button>
          )}
          <button
            onClick={() => fetchWaitlist()}
            className="px-3 py-1.5 text-sm font-mono text-terminal-muted hover:text-terminal-accent 
                     border border-terminal-border hover:border-terminal-accent rounded transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Stats */}
      {data && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
            <div className="text-2xl font-mono font-bold text-yellow-500">
              {data.stats.pending}
            </div>
            <div className="text-sm text-terminal-muted">Pending</div>
          </div>
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
            <div className="text-2xl font-mono font-bold text-terminal-accent">
              {data.stats.invited}
            </div>
            <div className="text-sm text-terminal-muted">Invited</div>
          </div>
          <div className="bg-terminal-surface border border-terminal-border rounded-lg p-4">
            <div className="text-2xl font-mono font-bold text-terminal-text">
              {data.stats.total}
            </div>
            <div className="text-sm text-terminal-muted">Total</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <span className="text-sm text-terminal-muted">Show:</span>
        <div className="flex gap-2">
          {(['pending', 'invited', 'all'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-sm font-mono rounded transition-colors capitalize ${
                filter === f
                  ? 'bg-terminal-accent text-terminal-bg'
                  : 'text-terminal-muted hover:text-terminal-text border border-terminal-border'
              }`}
            >
              {f}
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
          <div className="text-terminal-muted">Loading waitlist...</div>
        </div>
      )}

      {/* Waitlist Table */}
      {!loading && data && (
        <div className="bg-terminal-surface border border-terminal-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-terminal-border bg-terminal-bg/50">
                <th className="px-4 py-3 text-left text-xs font-mono text-terminal-muted uppercase tracking-wide">
                  Email
                </th>
                <th className="px-4 py-3 text-left text-xs font-mono text-terminal-muted uppercase tracking-wide">
                  Source
                </th>
                <th className="px-4 py-3 text-left text-xs font-mono text-terminal-muted uppercase tracking-wide">
                  Requested
                </th>
                <th className="px-4 py-3 text-left text-xs font-mono text-terminal-muted uppercase tracking-wide">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-mono text-terminal-muted uppercase tracking-wide">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {data.entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-terminal-muted">
                    No entries found.
                  </td>
                </tr>
              ) : (
                data.entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="border-b border-terminal-border/50 hover:bg-terminal-bg/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span className="text-terminal-text font-mono text-sm">
                        {entry.email}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-terminal-muted text-sm">
                        {entry.source || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-terminal-muted text-sm">
                        {formatDate(entry.createdAt)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {entry.invitedAt ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-mono rounded bg-terminal-accent/20 text-terminal-accent">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          Invited {formatDate(entry.invitedAt)}
                        </span>
                      ) : successIds.has(entry.id) ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-mono rounded bg-terminal-accent/20 text-terminal-accent">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          Sent!
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-mono rounded bg-yellow-500/20 text-yellow-500">
                          Pending
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!entry.invitedAt && !successIds.has(entry.id) && (
                        <button
                          onClick={() => sendInvite(entry)}
                          disabled={sendingIds.has(entry.id)}
                          className="px-3 py-1 text-xs font-mono rounded transition-colors
                                   bg-terminal-accent/10 text-terminal-accent hover:bg-terminal-accent hover:text-terminal-bg
                                   disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {sendingIds.has(entry.id) ? (
                            <span className="flex items-center gap-1.5">
                              <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                              </svg>
                              Sending...
                            </span>
                          ) : (
                            'Send Invite'
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Count */}
      {data && (
        <div className="text-center text-sm text-terminal-muted">
          Showing {data.entries.length} entries
        </div>
      )}
    </div>
  );
}
