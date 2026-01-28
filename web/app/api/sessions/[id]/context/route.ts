/**
 * Session Context API Route
 * 
 * GET /api/sessions/[id]/context - Get anonymized session context for feedback
 * 
 * Returns:
 * - Last 10 messages with toolsUsed
 * - Session metadata (model, reasoning, entities, title)
 * - Anonymized user info (no PII, just flags)
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';

interface RouteParams {
  params: Promise<{ id: string }>;
}

// Maximum number of recent messages to include
const MAX_MESSAGES = 10;

// GET /api/sessions/[id]/context
export async function GET(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const session = await getServerSession(authOptions);
  
  try {
    // Fetch the chat session with messages
    const chatSession = await prisma.chatSession.findUnique({
      where: { id },
      include: {
        messages: {
          orderBy: { createdAt: 'desc' },
          take: MAX_MESSAGES,
          select: {
            role: true,
            content: true,
            toolsUsed: true,
            createdAt: true,
          },
        },
        user: {
          select: {
            id: true,
            // Only select non-PII fields for anonymized metadata
          },
        },
      },
    });

    if (!chatSession) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    // Check if user has API keys (anonymized - just a boolean flag)
    let hasApiKeys = false;
    if (chatSession.userId) {
      const apiKeyCount = await prisma.userApiKey.count({
        where: { 
          userId: chatSession.userId,
          isActive: true,
        },
      });
      hasApiKeys = apiKeyCount > 0;
    }

    // Build the context snapshot
    const contextSnapshot = {
      // Recent messages (reversed to chronological order)
      recentMessages: chatSession.messages.reverse().map(msg => ({
        role: msg.role,
        content: msg.content.slice(0, 2000), // Truncate long messages
        toolsUsed: msg.toolsUsed,
        timestamp: msg.createdAt.toISOString(),
      })),
      
      // Session metadata
      sessionMeta: {
        model: chatSession.model,
        reasoning: chatSession.reasoning,
        entities: chatSession.entities,
        title: chatSession.title,
        createdAt: chatSession.createdAt.toISOString(),
      },
      
      // Anonymized user info (no PII)
      userMeta: {
        isAuthenticated: !!session?.user?.id,
        hasApiKeys,
        // Don't include email, name, or any identifying information
      },
    };

    return NextResponse.json(contextSnapshot);
  } catch (error) {
    console.error('Failed to get session context:', error);
    return NextResponse.json({ error: 'Failed to get session context' }, { status: 500 });
  }
}
