/**
 * Feedback API Routes
 * 
 * POST /api/feedback - Submit feedback for a message
 * GET /api/feedback - Get feedback stats and list (admin only for full data)
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';

// Context snapshot structure for feedback reports
interface ContextSnapshot {
  recentMessages: Array<{
    role: string;
    content: string;
    toolsUsed: string[];
    timestamp: string;
  }>;
  sessionMeta: {
    model: string | null;
    reasoning: string | null;
    entities: unknown;
    title: string | null;
    createdAt: string;
  };
  userMeta: {
    isAuthenticated: boolean;
    hasApiKeys: boolean;
  };
}

interface FeedbackRequest {
  messageId: string;
  type: 'up' | 'down';
  comment?: string;
  sessionId?: string;
  messageContent?: string;
  contextSnapshot?: ContextSnapshot;
}

// POST /api/feedback - Submit feedback
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    const body = await request.json() as FeedbackRequest;
    
    const { messageId, type, comment, sessionId, messageContent, contextSnapshot } = body;

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

    // Create feedback record with context snapshot
    const feedback = await prisma.messageFeedback.create({
      data: {
        userId: session?.user?.id || null,
        sessionId: sessionId || null,
        messageId,
        type,
        comment: comment || null,
        messageContent: messageContent || null,
        contextSnapshot: contextSnapshot || null,
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

// GET /api/feedback - Get feedback stats and list
export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  const isAdmin = session?.user?.role === 'admin';
  
  // Parse query params for filtering
  const { searchParams } = new URL(request.url);
  const typeFilter = searchParams.get('type'); // 'up' | 'down' | null
  const limit = Math.min(parseInt(searchParams.get('limit') || '50'), 100);
  const offset = parseInt(searchParams.get('offset') || '0');
  const includeContext = searchParams.get('includeContext') === 'true';
  
  try {
    // Build where clause
    const whereClause: { type?: string } = {};
    if (typeFilter === 'up' || typeFilter === 'down') {
      whereClause.type = typeFilter;
    }

    // Get stats (available to all)
    const [totalUp, totalDown] = await Promise.all([
      prisma.messageFeedback.count({ where: { type: 'up' } }),
      prisma.messageFeedback.count({ where: { type: 'down' } }),
    ]);

    // For non-admins, return only stats
    if (!isAdmin) {
      return NextResponse.json({
        stats: {
          totalUp,
          totalDown,
          total: totalUp + totalDown,
          positiveRate: totalUp + totalDown > 0 
            ? Math.round((totalUp / (totalUp + totalDown)) * 100) 
            : 0,
        },
        feedback: [], // No detailed feedback for non-admins
        isAdmin: false,
      });
    }

    // For admins, get full feedback list with optional context
    const feedbackList = await prisma.messageFeedback.findMany({
      where: whereClause,
      take: limit,
      skip: offset,
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        type: true,
        comment: true,
        messageContent: true,
        sessionId: true,
        contextSnapshot: includeContext,
        createdAt: true,
      },
    });

    // Get total count for pagination
    const totalCount = await prisma.messageFeedback.count({ where: whereClause });

    return NextResponse.json({
      stats: {
        totalUp,
        totalDown,
        total: totalUp + totalDown,
        positiveRate: totalUp + totalDown > 0 
          ? Math.round((totalUp / (totalUp + totalDown)) * 100) 
          : 0,
      },
      feedback: feedbackList.map(f => ({
        id: f.id,
        type: f.type,
        comment: f.comment,
        messageContent: f.messageContent,
        sessionId: f.sessionId,
        contextSnapshot: includeContext ? f.contextSnapshot : undefined,
        createdAt: f.createdAt.toISOString(),
      })),
      pagination: {
        total: totalCount,
        limit,
        offset,
        hasMore: offset + limit < totalCount,
      },
      isAdmin: true,
    });
  } catch (error) {
    console.error('Failed to get feedback stats:', error);
    return NextResponse.json(
      { error: 'Failed to get feedback stats' },
      { status: 500 }
    );
  }
}
