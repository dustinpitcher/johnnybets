/**
 * Internal API for backend services to fetch user credentials.
 * 
 * This endpoint is protected by an internal API key and should only be
 * called by the Python backend, not by client-side code.
 */
import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/db';
import { decrypt } from '@/lib/crypto';

// Internal API key for backend-to-backend auth
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY;

export async function GET(request: NextRequest) {
  // Verify internal API key
  const authHeader = request.headers.get('Authorization');
  const providedKey = authHeader?.replace('Bearer ', '');
  
  if (!INTERNAL_API_KEY || providedKey !== INTERNAL_API_KEY) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const userId = searchParams.get('userId');
  const provider = searchParams.get('provider');

  if (!userId || !provider) {
    return NextResponse.json(
      { error: 'userId and provider are required' },
      { status: 400 }
    );
  }

  try {
    const apiKey = await prisma.userApiKey.findUnique({
      where: {
        userId_provider: {
          userId,
          provider,
        },
      },
    });

    if (!apiKey || !apiKey.isActive) {
      return NextResponse.json({
        found: false,
        message: `No ${provider} credentials configured for this user`,
      });
    }

    // Decrypt and return credentials
    const credentials: Record<string, string> = {};
    
    if (apiKey.apiKey) {
      credentials.apiKey = decrypt(apiKey.apiKey);
    }
    if (apiKey.apiSecret) {
      credentials.apiSecret = decrypt(apiKey.apiSecret);
    }

    // Update last used timestamp
    await prisma.userApiKey.update({
      where: { id: apiKey.id },
      data: { lastUsedAt: new Date() },
    });

    return NextResponse.json({
      found: true,
      credentials,
    });
  } catch (error) {
    console.error('Error fetching user credentials:', error);
    return NextResponse.json(
      { error: 'Failed to fetch credentials' },
      { status: 500 }
    );
  }
}
