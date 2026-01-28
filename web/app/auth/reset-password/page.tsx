'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isValidating, setIsValidating] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isTokenValid, setIsTokenValid] = useState(false);

  // Validate token on mount
  useEffect(() => {
    async function validateToken() {
      if (!token) {
        setError('Missing reset token. Please request a new password reset link.');
        setIsValidating(false);
        return;
      }

      try {
        const response = await fetch(`/api/auth/reset-password?token=${token}`);
        const data = await response.json();

        if (data.valid) {
          setIsTokenValid(true);
        } else {
          setError(data.error === 'Token expired' 
            ? 'This reset link has expired. Please request a new one.'
            : data.error === 'Token already used'
            ? 'This reset link has already been used. Please request a new one.'
            : 'Invalid reset link. Please request a new password reset.');
        }
      } catch (err) {
        setError('Failed to validate reset link. Please try again.');
      } finally {
        setIsValidating(false);
      }
    }

    validateToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!password || !confirmPassword) {
      setError('Both password fields are required');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || 'Something went wrong');
        return;
      }

      setIsSuccess(true);

      // Redirect to signin after 3 seconds
      setTimeout(() => {
        router.push('/auth/signin');
      }, 3000);
    } catch (err) {
      setError('Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state while validating token
  if (isValidating) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin w-8 h-8 border-2 border-terminal-accent border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-terminal-muted">Validating reset link...</p>
      </div>
    );
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="text-center py-4">
        <div className="w-16 h-16 bg-terminal-accent/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-terminal-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-lg text-terminal-text mb-2">Password Reset!</h2>
        <p className="text-terminal-muted text-sm mb-4">
          Your password has been updated. Redirecting to sign in...
        </p>
        <Link
          href="/auth/signin"
          className="text-terminal-accent hover:underline text-sm"
        >
          Sign in now →
        </Link>
      </div>
    );
  }

  // Invalid token state
  if (!isTokenValid) {
    return (
      <div className="text-center py-4">
        <div className="w-16 h-16 bg-terminal-error/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-terminal-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 className="text-lg text-terminal-text mb-2">Invalid Reset Link</h2>
        <p className="text-terminal-muted text-sm mb-4">{error}</p>
        <Link
          href="/auth/forgot-password"
          className="inline-block px-4 py-2 bg-terminal-accent text-terminal-bg rounded-lg
                   font-medium hover:bg-terminal-accent/80 transition-colors"
        >
          Request New Link
        </Link>
      </div>
    );
  }

  // Reset form
  return (
    <>
      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-terminal-error/10 border border-terminal-error/30 rounded-lg">
          <p className="text-sm text-terminal-error">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="password" className="block text-sm text-terminal-muted mb-1">
            New Password
          </label>
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
            autoComplete="new-password"
            minLength={6}
            autoFocus
          />
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm text-terminal-muted mb-1">
            Confirm New Password
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

        <button
          type="submit"
          disabled={isLoading}
          className="w-full px-4 py-3 bg-terminal-accent text-terminal-bg rounded-lg
                   font-medium hover:bg-terminal-accent/80 transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Resetting...' : 'Reset Password'}
        </button>
      </form>

      <div className="mt-6 text-center">
        <Link
          href="/auth/signin"
          className="text-terminal-accent hover:underline text-sm"
        >
          ← Back to sign in
        </Link>
      </div>
    </>
  );
}

function ResetPasswordLoading() {
  return (
    <div className="text-center py-8">
      <div className="animate-pulse">
        <div className="h-8 w-32 bg-terminal-surface rounded mx-auto mb-4"></div>
        <div className="h-4 w-48 bg-terminal-surface rounded mx-auto"></div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-terminal-bg flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold text-terminal-accent glow-green">
            JohnnyBets
          </Link>
          <h1 className="text-xl text-terminal-text mt-4">
            Set a new password
          </h1>
          <p className="text-terminal-muted mt-2">
            Enter your new password below
          </p>
        </div>

        {/* Form */}
        <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6">
          <Suspense fallback={<ResetPasswordLoading />}>
            <ResetPasswordForm />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
