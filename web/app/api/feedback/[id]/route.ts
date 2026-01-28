/**
 * Single Feedback API Route
 * 
 * GET /api/feedback/[id] - Get full feedback details (admin only)
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';

interface RouteParams {
  params: Promise<{ id: string }>;
}

// GET /api/feedback/[id] - Get full feedback with context
export async function GET(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const session = await getServerSession(authOptions);
  
  // Admin only
  if (session?.user?.role !== 'admin') {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
  }

  try {
    const feedback = await prisma.messageFeedback.findUnique({
      where: { id },
    });

    if (!feedback) {
      return NextResponse.json({ error: 'Feedback not found' }, { status: 404 });
    }

    return NextResponse.json({
      id: feedback.id,
      type: feedback.type,
      comment: feedback.comment,
      messageContent: feedback.messageContent,
      sessionId: feedback.sessionId,
      contextSnapshot: feedback.contextSnapshot,
      createdAt: feedback.createdAt.toISOString(),
    });
  } catch (error) {
    console.error('Failed to get feedback:', error);
    return NextResponse.json({ error: 'Failed to get feedback' }, { status: 500 });
  }
}
