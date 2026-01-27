import { NextRequest, NextResponse } from 'next/server';
import prisma from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { code } = body;

    // Validate input
    if (!code || typeof code !== 'string') {
      return NextResponse.json(
        { valid: false, reason: 'Invite code is required' },
        { status: 400 }
      );
    }

    const normalizedCode = code.trim().toUpperCase();

    // Find the invite code
    const inviteCode = await prisma.inviteCode.findUnique({
      where: { code: normalizedCode },
    });

    if (!inviteCode) {
      return NextResponse.json({ 
        valid: false, 
        reason: 'Invalid invite code' 
      });
    }

    // Check if expired
    if (inviteCode.expiresAt && new Date() > inviteCode.expiresAt) {
      return NextResponse.json({ 
        valid: false, 
        reason: 'This invite code has expired' 
      });
    }

    // Check if max uses reached
    if (inviteCode.useCount >= inviteCode.maxUses) {
      return NextResponse.json({ 
        valid: false, 
        reason: 'This invite code has reached its usage limit' 
      });
    }

    // Code is valid
    return NextResponse.json({ 
      valid: true,
      code: normalizedCode,
    });

  } catch (error) {
    console.error('Invite validation error:', error);
    return NextResponse.json(
      { valid: false, reason: 'Failed to validate invite code' },
      { status: 500 }
    );
  }
}
