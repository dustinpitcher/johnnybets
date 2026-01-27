/**
 * Sessions API Routes
 * 
 * GET /api/sessions - List user's sessions
 * POST /api/sessions - Create a new session
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';

// GET /api/sessions - List user's sessions
export async function GET() {
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const sessions = await prisma.chatSession.findMany({
      where: { userId: session.user.id },
      include: {
        messages: {
          orderBy: { createdAt: 'asc' },
        },
      },
      orderBy: { updatedAt: 'desc' },
    });

    // Transform to match frontend interface
    const transformed = sessions.map((s) => ({
      id: s.id,
      title: s.title || 'New Session',
      messages: s.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.createdAt.toISOString(),
      })),
      createdAt: s.createdAt.toISOString(),
      updatedAt: s.updatedAt.toISOString(),
      tags: (s.entities as string[]) || [],
    }));

    return NextResponse.json(transformed);
  } catch (error) {
    console.error('Failed to fetch sessions:', error);
    return NextResponse.json({ error: 'Failed to fetch sessions' }, { status: 500 });
  }
}

// POST /api/sessions - Create a new session
export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json().catch(() => ({}));
    const { title, firstMessage } = body as { title?: string; firstMessage?: string };

    const chatSession = await prisma.chatSession.create({
      data: {
        userId: session.user.id,
        title: title || (firstMessage ? firstMessage.slice(0, 50) : 'New Session'),
        entities: [],
      },
    });

    return NextResponse.json({
      id: chatSession.id,
      title: chatSession.title || 'New Session',
      messages: [],
      createdAt: chatSession.createdAt.toISOString(),
      updatedAt: chatSession.updatedAt.toISOString(),
      tags: [],
    });
  } catch (error) {
    console.error('Failed to create session:', error);
    return NextResponse.json({ error: 'Failed to create session' }, { status: 500 });
  }
}
