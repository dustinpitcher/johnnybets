'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to feedback page by default
    router.replace('/admin/feedback');
  }, [router]);

  return (
    <div className="flex items-center justify-center py-12">
      <div className="text-terminal-muted">Redirecting...</div>
    </div>
  );
}
