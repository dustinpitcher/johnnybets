/**
 * Feedback API Routes
 * 
 * POST /api/feedback - Submit feedback for a message
 * GET /api/feedback - Get feedback stats (admin only, future)
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';

interface FeedbackRequest {
  messageId: string;
  type: 'up' | 'down';
  comment?: string;
  sessionId?: string;
  messageContent?: string;
}

// POST /api/feedback - Submit feedback
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    const body = await request.json() as FeedbackRequest;
    
    const { messageId, type, comment, sessionId, messageContent } = body;

    // Validate required fields
    if (!messageId || !type) {
      return NextResponse.json(
        { error: 'messageId and type are required' },
        { status: 400 }
      );
    }

    if (type !== 'up' && type !== 'down') {
      return NextResponse.json(
        { error: 'type must be "up" or "down"' },
        { status: 400 }
      );
    }

    // Create feedback record
    const feedback = await prisma.messageFeedback.create({
      data: {
        userId: session?.user?.id || null,
        sessionId: sessionId || null,
        messageId,
        type,
        comment: comment || null,
        messageContent: messageContent || null,
      },
    });

    return NextResponse.json({
      id: feedback.id,
      type: feedback.type,
      createdAt: feedback.createdAt.toISOString(),
    });
  } catch (error) {
    console.error('Failed to submit feedback:', error);
    return NextResponse.json(
      { error: 'Failed to submit feedback' },
      { status: 500 }
    );
  }
}

// GET /api/feedback - Get feedback stats
export async function GET() {
  const session = await getServerSession(authOptions);
  
  // For now, anyone can see aggregate stats
  // Later: restrict to admin users
  
  try {
    const [totalUp, totalDown, recentFeedback] = await Promise.all([
      prisma.messageFeedback.count({ where: { type: 'up' } }),
      prisma.messageFeedback.count({ where: { type: 'down' } }),
      prisma.messageFeedback.findMany({
        take: 10,
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          type: true,
          comment: true,
          createdAt: true,
        },
      }),
    ]);

    return NextResponse.json({
      stats: {
        totalUp,
        totalDown,
        total: totalUp + totalDown,
        positiveRate: totalUp + totalDown > 0 
          ? Math.round((totalUp / (totalUp + totalDown)) * 100) 
          : 0,
      },
      recent: recentFeedback.map(f => ({
        id: f.id,
        type: f.type,
        comment: f.comment,
        createdAt: f.createdAt.toISOString(),
      })),
    });
  } catch (error) {
    console.error('Failed to get feedback stats:', error);
    return NextResponse.json(
      { error: 'Failed to get feedback stats' },
      { status: 500 }
    );
  }
}
