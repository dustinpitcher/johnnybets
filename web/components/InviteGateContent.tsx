'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

type Tab = 'waitlist' | 'invite';

interface InviteGateContentProps {
  onClose: () => void;
}

export default function InviteGateContent({ onClose }: InviteGateContentProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>('waitlist');
  const [email, setEmail] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleWaitlistSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: 'invite_gate' }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: data.message || "You're on the list!" });
        setEmail('');
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to join waitlist' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Something went wrong. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await fetch('/api/invite/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: inviteCode }),
      });

      const data = await response.json();

      if (data.valid) {
        // Redirect to sign up with invite code
        onClose();
        router.push(`/auth/signin?invite=${encodeURIComponent(data.code)}&mode=signup`);
      } else {
        setMessage({ type: 'error', text: data.reason || 'Invalid invite code' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Something went wrong. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header message */}
      <div className="text-center">
        <p className="text-terminal-text text-lg mb-2">
          We're currently in <span className="text-terminal-accent font-semibold">invite-only beta</span>.
        </p>
        <p className="text-terminal-muted text-sm">
          Join the waitlist or enter your invite code to get access.
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex border-b border-terminal-border">
        <button
          onClick={() => { setActiveTab('waitlist'); setMessage(null); }}
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            activeTab === 'waitlist'
              ? 'text-terminal-accent border-b-2 border-terminal-accent'
              : 'text-terminal-muted hover:text-terminal-text'
          }`}
        >
          Join Waitlist
        </button>
        <button
          onClick={() => { setActiveTab('invite'); setMessage(null); }}
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            activeTab === 'invite'
              ? 'text-terminal-accent border-b-2 border-terminal-accent'
              : 'text-terminal-muted hover:text-terminal-text'
          }`}
        >
          Have an Invite
        </button>
      </div>

      {/* Message display */}
      {message && (
        <div
          className={`p-3 rounded text-sm ${
            message.type === 'success'
              ? 'bg-terminal-accent/10 text-terminal-accent border border-terminal-accent/30'
              : 'bg-terminal-error/10 text-terminal-error border border-terminal-error/30'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Waitlist form */}
      {activeTab === 'waitlist' && (
        <form onSubmit={handleWaitlistSubmit} className="space-y-4">
          <div>
            <label htmlFor="waitlist-email" className="block text-sm text-terminal-muted mb-2">
              Email address
            </label>
            <input
              id="waitlist-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              disabled={isLoading}
              className="w-full px-4 py-3 bg-terminal-bg border border-terminal-border rounded-lg 
                       text-terminal-text placeholder-terminal-muted
                       focus:outline-none focus:ring-1 focus:ring-terminal-accent focus:border-terminal-accent
                       disabled:opacity-50 text-[16px]"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !email}
            className="w-full py-3 bg-terminal-accent text-terminal-bg font-medium rounded-lg
                     hover:bg-terminal-accent/80 transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Joining...' : 'Join the Waitlist'}
          </button>
        </form>
      )}

      {/* Invite code form */}
      {activeTab === 'invite' && (
        <form onSubmit={handleInviteSubmit} className="space-y-4">
          <div>
            <label htmlFor="invite-code" className="block text-sm text-terminal-muted mb-2">
              Invite code
            </label>
            <input
              id="invite-code"
              type="text"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
              placeholder="XXXX-XXXX"
              required
              disabled={isLoading}
              className="w-full px-4 py-3 bg-terminal-bg border border-terminal-border rounded-lg 
                       text-terminal-text placeholder-terminal-muted font-mono tracking-wider
                       focus:outline-none focus:ring-1 focus:ring-terminal-accent focus:border-terminal-accent
                       disabled:opacity-50 text-[16px] uppercase"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !inviteCode}
            className="w-full py-3 bg-terminal-accent text-terminal-bg font-medium rounded-lg
                     hover:bg-terminal-accent/80 transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Validating...' : 'Continue with Invite'}
          </button>
        </form>
      )}

      {/* Sign in link for existing users */}
      <div className="text-center pt-2 border-t border-terminal-border">
        <p className="text-terminal-muted text-sm">
          Already have an account?{' '}
          <button
            onClick={() => {
              onClose();
              router.push('/auth/signin');
            }}
            className="text-terminal-accent hover:underline"
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
}
