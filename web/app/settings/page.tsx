'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface ApiKey {
  id: string;
  provider: string;
  label: string | null;
  apiKey: string | null;
  isActive: boolean;
  lastUsedAt: string | null;
  createdAt: string;
}

interface ProviderConfig {
  name: string;
  description: string;
  fields: { key: string; label: string; placeholder: string; type: 'text' | 'password' | 'file' }[];
  helpUrl?: string;
}

const PROVIDERS: Record<string, ProviderConfig> = {
  kalshi: {
    name: 'Kalshi',
    description: 'Connect your Kalshi account for prediction market data.',
    fields: [
      { key: 'apiKey', label: 'API Key ID', placeholder: 'Your Kalshi API Key ID', type: 'text' },
      { key: 'apiSecret', label: 'Private Key', placeholder: 'Paste your RSA private key contents', type: 'password' },
    ],
    helpUrl: 'https://kalshi.com/api',
  },
  x: {
    name: 'X (Twitter)',
    description: 'Connect your own X API for enhanced social intel.',
    fields: [
      { key: 'apiKey', label: 'API Key', placeholder: 'Your X API Key', type: 'text' },
      { key: 'apiSecret', label: 'API Secret', placeholder: 'Your X API Secret', type: 'password' },
    ],
    helpUrl: 'https://developer.x.com',
  },
};

export default function SettingsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Form state for adding new keys
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchApiKeys();
    }
  }, [session]);

  const fetchApiKeys = async () => {
    try {
      const res = await fetch('/api/user/api-keys');
      if (res.ok) {
        const data = await res.json();
        setApiKeys(data.apiKeys);
      }
    } catch (err) {
      console.error('Error fetching API keys:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveKey = async (provider: string) => {
    setSaving(provider);
    setError(null);
    setSuccess(null);

    try {
      const res = await fetch('/api/user/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          apiKey: formData.apiKey,
          apiSecret: formData.apiSecret,
          label: formData.label,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to save');
      }

      setSuccess(`${PROVIDERS[provider]?.name || provider} connected successfully!`);
      setEditingProvider(null);
      setFormData({});
      fetchApiKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save API key');
    } finally {
      setSaving(null);
    }
  };

  const handleDeleteKey = async (provider: string) => {
    if (!confirm(`Remove ${PROVIDERS[provider]?.name || provider} connection?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/user/api-keys?provider=${provider}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        throw new Error('Failed to delete');
      }

      setSuccess(`${PROVIDERS[provider]?.name || provider} disconnected.`);
      fetchApiKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete API key');
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-terminal-bg flex items-center justify-center">
        <div className="text-terminal-accent animate-pulse">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  const getConnectedKey = (provider: string) => 
    apiKeys.find((k) => k.provider === provider);

  return (
    <div className="min-h-screen bg-terminal-bg text-terminal-text">
      {/* Header */}
      <header className="border-b border-terminal-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-terminal-accent hover:text-terminal-accent/80 transition-colors">
              ← Back
            </Link>
            <h1 className="text-xl font-semibold">Settings</h1>
          </div>
          <div className="text-sm text-terminal-muted">
            {session.user?.email}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Alerts */}
        {error && (
          <div className="mb-6 p-4 bg-terminal-error/10 border border-terminal-error rounded-lg text-terminal-error">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-6 p-4 bg-terminal-success/10 border border-terminal-success rounded-lg text-terminal-success">
            {success}
          </div>
        )}

        {/* Connected Accounts Section */}
        <section>
          <h2 className="text-lg font-semibold mb-2">Connected Accounts</h2>
          <p className="text-terminal-muted mb-6">
            Connect your own API keys to unlock additional features. Your credentials are encrypted at rest.
          </p>

          <div className="space-y-4">
            {Object.entries(PROVIDERS).map(([providerId, config]) => {
              const connectedKey = getConnectedKey(providerId);
              const isEditing = editingProvider === providerId;

              return (
                <div
                  key={providerId}
                  className="border border-terminal-border rounded-lg p-6 bg-terminal-surface"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-terminal-text">{config.name}</h3>
                      <p className="text-sm text-terminal-muted mt-1">{config.description}</p>
                    </div>
                    {connectedKey && !isEditing && (
                      <span className="px-2 py-1 text-xs rounded bg-terminal-success/20 text-terminal-success">
                        Connected
                      </span>
                    )}
                  </div>

                  {connectedKey && !isEditing ? (
                    // Connected state
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-terminal-muted">
                        <span className="font-mono">{connectedKey.apiKey || '****'}</span>
                        {connectedKey.lastUsedAt && (
                          <span className="ml-4">
                            Last used: {new Date(connectedKey.lastUsedAt).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setEditingProvider(providerId);
                            setFormData({});
                          }}
                          className="px-3 py-1.5 text-sm text-terminal-muted hover:text-terminal-text transition-colors"
                        >
                          Update
                        </button>
                        <button
                          onClick={() => handleDeleteKey(providerId)}
                          className="px-3 py-1.5 text-sm text-terminal-error hover:text-terminal-error/80 transition-colors"
                        >
                          Disconnect
                        </button>
                      </div>
                    </div>
                  ) : isEditing ? (
                    // Editing state
                    <div className="space-y-4">
                      {config.fields.map((field) => (
                        <div key={field.key}>
                          <label className="block text-sm font-medium text-terminal-muted mb-1">
                            {field.label}
                          </label>
                          {field.key === 'apiSecret' ? (
                            <textarea
                              value={formData[field.key] || ''}
                              onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                              placeholder={field.placeholder}
                              rows={4}
                              className="w-full px-3 py-2 bg-terminal-bg border border-terminal-border rounded-lg 
                                       text-terminal-text placeholder-terminal-muted/50 font-mono text-sm
                                       focus:outline-none focus:ring-2 focus:ring-terminal-accent/50"
                            />
                          ) : (
                            <input
                              type={field.type}
                              value={formData[field.key] || ''}
                              onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                              placeholder={field.placeholder}
                              className="w-full px-3 py-2 bg-terminal-bg border border-terminal-border rounded-lg 
                                       text-terminal-text placeholder-terminal-muted/50
                                       focus:outline-none focus:ring-2 focus:ring-terminal-accent/50"
                            />
                          )}
                        </div>
                      ))}
                      
                      <div className="flex items-center justify-between pt-2">
                        {config.helpUrl && (
                          <a
                            href={config.helpUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-terminal-accent hover:underline"
                          >
                            How to get API keys →
                          </a>
                        )}
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setEditingProvider(null);
                              setFormData({});
                            }}
                            className="px-4 py-2 text-sm text-terminal-muted hover:text-terminal-text transition-colors"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleSaveKey(providerId)}
                            disabled={saving === providerId || !formData.apiKey}
                            className="px-4 py-2 text-sm bg-terminal-accent text-terminal-bg rounded-lg
                                     hover:bg-terminal-accent/80 disabled:opacity-50 disabled:cursor-not-allowed
                                     transition-colors"
                          >
                            {saving === providerId ? 'Saving...' : 'Save'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    // Not connected state
                    <button
                      onClick={() => setEditingProvider(providerId)}
                      className="px-4 py-2 text-sm border border-terminal-accent text-terminal-accent rounded-lg
                               hover:bg-terminal-accent/10 transition-colors"
                    >
                      Connect {config.name}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Security Note */}
        <section className="mt-12 p-4 border border-terminal-border rounded-lg bg-terminal-surface/50">
          <h3 className="font-medium text-terminal-text mb-2">🔒 Security</h3>
          <ul className="text-sm text-terminal-muted space-y-1">
            <li>• Your API keys are encrypted using AES-256-GCM before storage</li>
            <li>• Keys are only decrypted when needed for API calls</li>
            <li>• We never log or display your full API keys</li>
            <li>• You can revoke access at any time by disconnecting</li>
          </ul>
        </section>
      </main>
    </div>
  );
}
