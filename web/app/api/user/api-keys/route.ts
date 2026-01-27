/**
 * API routes for managing user API keys (BYOK)
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { encrypt, decrypt, maskApiKey } from '@/lib/crypto';

// Supported providers
const SUPPORTED_PROVIDERS = ['kalshi', 'x'] as const;
type Provider = typeof SUPPORTED_PROVIDERS[number];

interface ApiKeyInput {
  provider: Provider;
  apiKey: string;
  apiSecret?: string;
  label?: string;
}

/**
 * GET /api/user/api-keys
 * List all API keys for the current user (masked)
 */
export async function GET() {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const apiKeys = await prisma.userApiKey.findMany({
      where: { userId: session.user.id },
      select: {
        id: true,
        provider: true,
        label: true,
        isActive: true,
        lastUsedAt: true,
        createdAt: true,
        apiKey: true, // We'll mask this
      },
    });

    // Mask the API keys for display
    const maskedKeys = apiKeys.map((key) => ({
      ...key,
      apiKey: key.apiKey ? maskApiKey(decrypt(key.apiKey)) : null,
      hasApiSecret: false, // We don't return the secret at all
    }));

    return NextResponse.json({ apiKeys: maskedKeys });
  } catch (error) {
    console.error('Error fetching API keys:', error);
    return NextResponse.json(
      { error: 'Failed to fetch API keys' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/user/api-keys
 * Create or update an API key for a provider
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body: ApiKeyInput = await request.json();
    
    // Validate provider
    if (!SUPPORTED_PROVIDERS.includes(body.provider)) {
      return NextResponse.json(
        { error: `Unsupported provider. Supported: ${SUPPORTED_PROVIDERS.join(', ')}` },
        { status: 400 }
      );
    }

    // Validate API key
    if (!body.apiKey || body.apiKey.trim().length === 0) {
      return NextResponse.json(
        { error: 'API key is required' },
        { status: 400 }
      );
    }

    // Encrypt the credentials
    const encryptedApiKey = encrypt(body.apiKey.trim());
    const encryptedApiSecret = body.apiSecret ? encrypt(body.apiSecret.trim()) : null;

    // Upsert the API key (one per provider per user)
    const apiKey = await prisma.userApiKey.upsert({
      where: {
        userId_provider: {
          userId: session.user.id,
          provider: body.provider,
        },
      },
      update: {
        apiKey: encryptedApiKey,
        apiSecret: encryptedApiSecret,
        label: body.label,
        isActive: true,
        updatedAt: new Date(),
      },
      create: {
        userId: session.user.id,
        provider: body.provider,
        apiKey: encryptedApiKey,
        apiSecret: encryptedApiSecret,
        label: body.label,
      },
    });

    return NextResponse.json({
      success: true,
      apiKey: {
        id: apiKey.id,
        provider: apiKey.provider,
        label: apiKey.label,
        isActive: apiKey.isActive,
        createdAt: apiKey.createdAt,
      },
    });
  } catch (error) {
    console.error('Error saving API key:', error);
    return NextResponse.json(
      { error: 'Failed to save API key' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/user/api-keys
 * Delete an API key by provider
 */
export async function DELETE(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const provider = searchParams.get('provider');

    if (!provider) {
      return NextResponse.json(
        { error: 'Provider is required' },
        { status: 400 }
      );
    }

    await prisma.userApiKey.deleteMany({
      where: {
        userId: session.user.id,
        provider: provider,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting API key:', error);
    return NextResponse.json(
      { error: 'Failed to delete API key' },
      { status: 500 }
    );
  }
}
