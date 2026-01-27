/**
 * Session by ID API Routes
 * 
 * GET /api/sessions/[id] - Get session with messages
 * PATCH /api/sessions/[id] - Update session (title, tags)
 * DELETE /api/sessions/[id] - Delete session
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';

interface RouteParams {
  params: Promise<{ id: string }>;
}

// GET /api/sessions/[id] - Get session with messages
export async function GET(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const chatSession = await prisma.chatSession.findFirst({
      where: {
        id,
        userId: session.user.id,
      },
      include: {
        messages: {
          orderBy: { createdAt: 'asc' },
        },
      },
    });

    if (!chatSession) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    return NextResponse.json({
      id: chatSession.id,
      title: chatSession.title || 'New Session',
      messages: chatSession.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.createdAt.toISOString(),
      })),
      createdAt: chatSession.createdAt.toISOString(),
      updatedAt: chatSession.updatedAt.toISOString(),
      tags: (chatSession.entities as string[]) || [],
    });
  } catch (error) {
    console.error('Failed to fetch session:', error);
    return NextResponse.json({ error: 'Failed to fetch session' }, { status: 500 });
  }
}

// PATCH /api/sessions/[id] - Update session
export async function PATCH(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { title, tags } = body as { title?: string; tags?: string[] };

    // First verify the session belongs to this user
    const existing = await prisma.chatSession.findFirst({
      where: {
        id,
        userId: session.user.id,
      },
    });

    if (!existing) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    const updated = await prisma.chatSession.update({
      where: { id },
      data: {
        ...(title !== undefined && { title }),
        ...(tags !== undefined && { entities: tags }),
      },
    });

    return NextResponse.json({
      id: updated.id,
      title: updated.title || 'New Session',
      updatedAt: updated.updatedAt.toISOString(),
      tags: (updated.entities as string[]) || [],
    });
  } catch (error) {
    console.error('Failed to update session:', error);
    return NextResponse.json({ error: 'Failed to update session' }, { status: 500 });
  }
}

// DELETE /api/sessions/[id] - Delete session
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    // First verify the session belongs to this user
    const existing = await prisma.chatSession.findFirst({
      where: {
        id,
        userId: session.user.id,
      },
    });

    if (!existing) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    await prisma.chatSession.delete({
      where: { id },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to delete session:', error);
    return NextResponse.json({ error: 'Failed to delete session' }, { status: 500 });
  }
}
