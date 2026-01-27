import { NextRequest, NextResponse } from 'next/server';
import prisma from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { code, maxUses = 1, note } = body;

    // Validate input
    if (!code || typeof code !== 'string') {
      return NextResponse.json(
        { error: 'Code is required' },
        { status: 400 }
      );
    }

    const normalizedCode = code.trim().toUpperCase();

    // Check if code already exists
    const existing = await prisma.inviteCode.findUnique({
      where: { code: normalizedCode },
    });

    if (existing) {
      return NextResponse.json(
        { error: 'Code already exists' },
        { status: 409 }
      );
    }

    // Create the invite code
    const inviteCode = await prisma.inviteCode.create({
      data: {
        code: normalizedCode,
        maxUses: maxUses,
        useCount: 0,
        note: note || null,
      },
    });

    return NextResponse.json({
      success: true,
      code: inviteCode.code,
      maxUses: inviteCode.maxUses,
      note: inviteCode.note,
    });

  } catch (error) {
    console.error('Create invite code error:', error);
    return NextResponse.json(
      { error: 'Failed to create invite code' },
      { status: 500 }
    );
  }
}
