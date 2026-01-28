/**
 * Session Messages API Routes
 * 
 * POST /api/sessions/[id]/messages - Add message to session
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';

interface RouteParams {
  params: Promise<{ id: string }>;
}

// Common team/sport keywords for tagging
const TAG_KEYWORDS = [
  'NFL', 'NHL', 'MLB', 'NBA',
  'Bills', 'Chiefs', 'Eagles', 'Cowboys', 'Patriots', '49ers', 'Packers', 'Bears',
  'Rangers', 'Bruins', 'Maple Leafs', 'Oilers', 'Penguins', 'Capitals',
  'Yankees', 'Dodgers', 'Red Sox', 'Cubs', 'Mets', 'Astros',
];

function extractTags(content: string): string[] {
  const tags: string[] = [];
  const lowerContent = content.toLowerCase();
  
  for (const keyword of TAG_KEYWORDS) {
    if (lowerContent.includes(keyword.toLowerCase())) {
      tags.push(keyword);
    }
  }
  
  return tags.slice(0, 5); // Max 5 tags
}

// POST /api/sessions/[id]/messages - Add message to session
export async function POST(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { role, content, toolsUsed } = body as { 
      role: string; 
      content: string; 
      toolsUsed?: string[];
    };

    if (!role || !content) {
      return NextResponse.json({ error: 'Role and content are required' }, { status: 400 });
    }

    // Verify the session belongs to this user
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

    // Create the message
    const message = await prisma.chatMessage.create({
      data: {
        sessionId: id,
        role,
        content,
        toolsUsed: toolsUsed || [],
      },
    });

    // Update session title if this is the first user message
    let newTitle = chatSession.title;
    if (role === 'user' && chatSession.messages.length === 0) {
      newTitle = content.slice(0, 50) + (content.length > 50 ? '...' : '');
    }

    // Extract and merge tags from user messages
    let newTags = (chatSession.entities as string[]) || [];
    if (role === 'user') {
      const extracted = extractTags(content);
      newTags = [...new Set([...newTags, ...extracted])].slice(0, 5);
    }

    // Update session metadata
    await prisma.chatSession.update({
      where: { id },
      data: {
        title: newTitle,
        entities: newTags,
      },
    });

    return NextResponse.json({
      id: message.id,
      role: message.role,
      content: message.content,
      timestamp: message.createdAt.toISOString(),
    });
  } catch (error) {
    console.error('Failed to add message:', error);
    return NextResponse.json({ error: 'Failed to add message' }, { status: 500 });
  }
}
