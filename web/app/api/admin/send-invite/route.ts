/**
 * Admin Send Invite API Route
 * 
 * POST /api/admin/send-invite
 * 
 * Sends invite notification email to a waitlist user.
 * Creates a new invite code if not provided.
 * Admin only.
 */
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { randomBytes } from 'crypto';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/db';
import { sendInviteNotification } from '@/lib/email';

// Generate a random invite code like "XXXX-XXXX"
function generateInviteCode(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // Removed confusing chars (I, O, 0, 1)
  let code = '';
  for (let i = 0; i < 8; i++) {
    if (i === 4) code += '-';
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}

export async function POST(request: NextRequest) {
  try {
    // Check admin auth
    const session = await getServerSession(authOptions);
    if (session?.user?.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    const body = await request.json();
    const { waitlistEntryId, inviteCodeId, email: directEmail } = body;

    let targetEmail: string;
    let waitlistEntry = null;

    // Either use waitlistEntryId to look up email, or use direct email
    if (waitlistEntryId) {
      waitlistEntry = await prisma.waitlistEntry.findUnique({
        where: { id: waitlistEntryId },
      });

      if (!waitlistEntry) {
        return NextResponse.json(
          { error: 'Waitlist entry not found' },
          { status: 404 }
        );
      }

      if (waitlistEntry.invitedAt) {
        return NextResponse.json(
          { error: 'This user has already been sent an invite' },
          { status: 400 }
        );
      }

      targetEmail = waitlistEntry.email;
    } else if (directEmail) {
      targetEmail = directEmail.toLowerCase().trim();
    } else {
      return NextResponse.json(
        { error: 'Either waitlistEntryId or email is required' },
        { status: 400 }
      );
    }

    // Get or create invite code
    let inviteCode;
    
    if (inviteCodeId) {
      // Use existing invite code
      inviteCode = await prisma.inviteCode.findUnique({
        where: { id: inviteCodeId },
      });

      if (!inviteCode) {
        return NextResponse.json(
          { error: 'Invite code not found' },
          { status: 404 }
        );
      }

      // Check if code is still usable
      if (inviteCode.expiresAt && new Date() > inviteCode.expiresAt) {
        return NextResponse.json(
          { error: 'This invite code has expired' },
          { status: 400 }
        );
      }

      if (inviteCode.useCount >= inviteCode.maxUses) {
        return NextResponse.json(
          { error: 'This invite code has reached its usage limit' },
          { status: 400 }
        );
      }
    } else {
      // Create a new invite code
      let code = generateInviteCode();
      
      // Ensure code is unique (unlikely collision but check anyway)
      let attempts = 0;
      while (attempts < 5) {
        const existing = await prisma.inviteCode.findUnique({
          where: { code },
        });
        if (!existing) break;
        code = generateInviteCode();
        attempts++;
      }

      inviteCode = await prisma.inviteCode.create({
        data: {
          code,
          maxUses: 1,
          useCount: 0,
          createdBy: session.user.id,
          note: waitlistEntry 
            ? `Sent to waitlist: ${targetEmail}` 
            : `Sent to: ${targetEmail}`,
          expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
        },
      });
    }

    // Send the invite email
    try {
      await sendInviteNotification(targetEmail, inviteCode.code);
    } catch (emailError) {
      console.error('Failed to send invite email:', emailError);
      return NextResponse.json(
        { error: 'Failed to send invite email. Please try again.' },
        { status: 500 }
      );
    }

    // Mark waitlist entry as invited (if applicable)
    if (waitlistEntry) {
      await prisma.waitlistEntry.update({
        where: { id: waitlistEntry.id },
        data: { invitedAt: new Date() },
      });
    }

    console.log(`Invite sent to ${targetEmail} with code ${inviteCode.code} by admin ${session.user.email}`);

    return NextResponse.json({
      success: true,
      email: targetEmail,
      inviteCode: inviteCode.code,
      inviteCodeId: inviteCode.id,
    });
  } catch (error) {
    console.error('Send invite error:', error);
    return NextResponse.json(
      { error: 'An error occurred. Please try again.' },
      { status: 500 }
    );
  }
}

/**
 * GET /api/admin/send-invite
 * 
 * List waitlist entries that haven't been invited yet.
 * Admin only.
 */
export async function GET(request: NextRequest) {
  try {
    // Check admin auth
    const session = await getServerSession(authOptions);
    if (session?.user?.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const showInvited = searchParams.get('showInvited') === 'true';
    const limit = parseInt(searchParams.get('limit') || '50', 10);

    const waitlistEntries = await prisma.waitlistEntry.findMany({
      where: showInvited ? {} : { invitedAt: null },
      orderBy: { createdAt: 'asc' }, // First come, first served
      take: limit,
    });

    const totalPending = await prisma.waitlistEntry.count({
      where: { invitedAt: null },
    });

    const totalInvited = await prisma.waitlistEntry.count({
      where: { invitedAt: { not: null } },
    });

    return NextResponse.json({
      entries: waitlistEntries.map(entry => ({
        id: entry.id,
        email: entry.email,
        source: entry.source,
        invitedAt: entry.invitedAt,
        createdAt: entry.createdAt,
      })),
      stats: {
        pending: totalPending,
        invited: totalInvited,
        total: totalPending + totalInvited,
      },
    });
  } catch (error) {
    console.error('List waitlist error:', error);
    return NextResponse.json(
      { error: 'An error occurred' },
      { status: 500 }
    );
  }
}
