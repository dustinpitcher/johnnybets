'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import Link from 'next/link';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'loading') return;
    
    if (!session?.user) {
      router.push('/auth/signin');
      return;
    }

    if (session.user.role !== 'admin') {
      router.push('/');
      return;
    }
  }, [session, status, router]);

  // Show loading state while checking auth
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-terminal-bg flex items-center justify-center">
        <div className="text-terminal-muted">Loading...</div>
      </div>
    );
  }

  // Show nothing if not admin (redirect will happen)
  if (!session?.user || session.user.role !== 'admin') {
    return (
      <div className="min-h-screen bg-terminal-bg flex items-center justify-center">
        <div className="text-terminal-error">Access denied. Admin only.</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-terminal-bg">
      {/* Admin Header */}
      <header className="border-b border-terminal-border bg-terminal-surface">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link 
              href="/" 
              className="text-terminal-accent font-mono font-bold text-lg hover:opacity-80"
            >
              JohnnyBets
            </Link>
            <span className="text-terminal-muted text-sm font-mono px-2 py-0.5 bg-terminal-bg rounded">
              Admin
            </span>
          </div>
          
          <nav className="flex items-center gap-4">
            <Link
              href="/admin/feedback"
              className="text-terminal-muted hover:text-terminal-accent text-sm font-mono transition-colors"
            >
              Feedback
            </Link>
            <Link
              href="/admin/invites"
              className="text-terminal-muted hover:text-terminal-accent text-sm font-mono transition-colors"
            >
              Invites
            </Link>
            <Link
              href="/"
              className="text-terminal-muted hover:text-terminal-text text-sm font-mono transition-colors"
            >
              Back to App
            </Link>
          </nav>
        </div>
      </header>

      {/* Admin Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  );
}
