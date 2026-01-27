'use client';

import { useSession, signIn, signOut } from 'next-auth/react';
import { useState } from 'react';

export default function UserMenu() {
  const { data: session, status } = useSession();
  const [isOpen, setIsOpen] = useState(false);

  if (status === 'loading') {
    return (
      <div className="w-8 h-8 rounded-full bg-terminal-surface animate-pulse" />
    );
  }

  if (!session) {
    return (
      <button
        onClick={() => signIn()}
        className="btn btn-ghost text-sm"
      >
        Sign In
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                 bg-terminal-surface border border-terminal-border
                 hover:border-terminal-accent transition-colors"
      >
        {session.user.image ? (
          <img
            src={session.user.image}
            alt={session.user.name || 'User'}
            className="w-6 h-6 rounded-full"
          />
        ) : (
          <div className="w-6 h-6 rounded-full bg-terminal-accent flex items-center justify-center text-terminal-bg text-xs font-bold">
            {session.user.name?.[0] || session.user.email?.[0] || '?'}
          </div>
        )}
        <span className="text-sm text-terminal-text hidden sm:block">
          {session.user.name || session.user.email?.split('@')[0]}
        </span>
        <span className="badge badge-free text-xs">
          {session.user.tier || 'Free'}
        </span>
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-56 bg-terminal-surface border border-terminal-border rounded-lg shadow-lg z-20">
            <div className="p-3 border-b border-terminal-border">
              <p className="text-sm font-medium text-terminal-text">
                {session.user.name || 'User'}
              </p>
              <p className="text-xs text-terminal-muted truncate">
                {session.user.email}
              </p>
            </div>
            
            <div className="p-1">
              <a
                href="/sessions"
                className="block px-3 py-2 text-sm text-terminal-text hover:bg-terminal-border rounded"
              >
                My Sessions
              </a>
              <a
                href="/settings"
                className="block px-3 py-2 text-sm text-terminal-text hover:bg-terminal-border rounded"
              >
                Settings
              </a>
            </div>
            
            <div className="p-1 border-t border-terminal-border">
              <button
                onClick={() => signOut()}
                className="w-full text-left px-3 py-2 text-sm text-terminal-error hover:bg-terminal-border rounded"
              >
                Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

