'use client';

import { signIn } from 'next-auth/react';
import { useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

function SignInForm() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || '/';
  const errorParam = searchParams.get('error');
  const inviteCodeParam = searchParams.get('invite');
  const modeParam = searchParams.get('mode');

  // Default to signup mode if invite code is present
  const [isSignUp, setIsSignUp] = useState(modeParam === 'signup' || !!inviteCodeParam);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [inviteCode, setInviteCode] = useState(inviteCodeParam || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(errorParam);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError('Email and password are required');
      return;
    }

    if (isSignUp && password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    // Require invite code for signup
    if (isSignUp && !inviteCode.trim()) {
      setError('Invite code is required to create an account');
      return;
    }

    setIsLoading(true);

    try {
      const result = await signIn('credentials', {
        email,
        password,
        action: isSignUp ? 'signup' : 'signin',
        inviteCode: isSignUp ? inviteCode.trim().toUpperCase() : undefined,
        redirect: false,
        callbackUrl,
      });

      if (result?.error) {
        setError(result.error);
      } else if (result?.ok) {
        // Redirect on success
        window.location.href = callbackUrl;
      }
    } catch (err) {
      setError('Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Header */}
      <div className="text-center mb-8">
        <Link href="/" className="text-2xl font-bold text-terminal-accent glow-green">
          JohnnyBets
        </Link>
        <h1 className="text-xl text-terminal-text mt-4">
          {isSignUp ? 'Create an account' : 'Welcome back'}
        </h1>
        <p className="text-terminal-muted mt-2">
          {isSignUp 
            ? 'Sign up to save your betting sessions' 
            : 'Sign in to access your saved sessions'}
        </p>
      </div>

      {/* Form */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6">
        {/* Error message */}
        {error && (
          <div className="mb-4 p-3 bg-terminal-error/10 border border-terminal-error/30 rounded-lg">
            <p className="text-sm text-terminal-error">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm text-terminal-muted mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-4 py-3 bg-terminal-bg border border-terminal-border rounded-lg
                       text-terminal-text placeholder-terminal-muted
                       focus:border-terminal-accent focus:ring-1 focus:ring-terminal-accent
                       focus:outline-none"
              required
              autoComplete="email"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label htmlFor="password" className="block text-sm text-terminal-muted">
                Password
              </label>
              {!isSignUp && (
                <Link
                  href="/auth/forgot-password"
                  className="text-xs text-terminal-accent hover:underline"
                >
                  Forgot password?
                </Link>
              )}
            </div>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-3 bg-terminal-bg border border-terminal-border rounded-lg
                       text-terminal-text placeholder-terminal-muted
                       focus:border-terminal-accent focus:ring-1 focus:ring-terminal-accent
                       focus:outline-none"
              required
              autoComplete={isSignUp ? 'new-password' : 'current-password'}
              minLength={6}
            />
          </div>

          {isSignUp && (
            <>
              <div>
                <label htmlFor="confirmPassword" className="block text-sm text-terminal-muted mb-1">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 bg-terminal-bg border border-terminal-border rounded-lg
                           text-terminal-text placeholder-terminal-muted
                           focus:border-terminal-accent focus:ring-1 focus:ring-terminal-accent
                           focus:outline-none"
                  required
                  autoComplete="new-password"
                  minLength={6}
                />
              </div>

              <div>
                <label htmlFor="inviteCode" className="block text-sm text-terminal-muted mb-1">
                  Invite Code
                </label>
                <input
                  id="inviteCode"
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                  placeholder="XXXX-XXXX"
                  className="w-full px-4 py-3 bg-terminal-bg border border-terminal-border rounded-lg
                           text-terminal-text placeholder-terminal-muted font-mono tracking-wider
                           focus:border-terminal-accent focus:ring-1 focus:ring-terminal-accent
                           focus:outline-none uppercase text-[16px]"
                  required
                />
                <p className="text-xs text-terminal-muted mt-1">
                  We&apos;re currently invite-only during beta.
                </p>
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full px-4 py-3 bg-terminal-accent text-terminal-bg rounded-lg
                     font-medium hover:bg-terminal-accent/80 transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading 
              ? (isSignUp ? 'Creating account...' : 'Signing in...') 
              : (isSignUp ? 'Create Account' : 'Sign In')}
          </button>
        </form>

        {/* Toggle sign in / sign up */}
        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError(null);
            }}
            className="text-terminal-accent hover:underline text-sm"
          >
            {isSignUp 
              ? 'Already have an account? Sign in' 
              : "Don't have an account? Sign up"}
          </button>
        </div>
      </div>

      {/* Footer - hide "continue without signing in" during invite-only beta */}
      {!inviteCodeParam && (
        <div className="mt-6 text-center">
          <Link href="/" className="text-terminal-muted hover:text-terminal-accent text-sm">
            ← Back to home
          </Link>
        </div>
      )}

      <p className="mt-8 text-center text-xs text-terminal-muted">
        By signing in, you agree to our Terms of Service and Privacy Policy.
      </p>

      {/* Invite-only notice */}
      {isSignUp && (
        <div className="mt-6 p-3 bg-terminal-accent/10 border border-terminal-accent/30 rounded-lg">
          <p className="text-xs text-terminal-accent">
            <strong>Invite Only:</strong> JohnnyBets is currently in private beta. You need an invite code to create an account.
          </p>
        </div>
      )}
    </>
  );
}

function SignInLoading() {
  return (
    <div className="text-center">
      <div className="animate-pulse">
        <div className="h-8 w-32 bg-terminal-surface rounded mx-auto mb-4"></div>
        <div className="h-4 w-48 bg-terminal-surface rounded mx-auto"></div>
      </div>
    </div>
  );
}

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-terminal-bg flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <Suspense fallback={<SignInLoading />}>
          <SignInForm />
        </Suspense>
      </div>
    </div>
  );
}
