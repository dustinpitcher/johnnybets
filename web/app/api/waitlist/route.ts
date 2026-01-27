import { NextRequest, NextResponse } from 'next/server';
import prisma from '@/lib/db';

// Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, source } = body;

    // Validate email
    if (!email || typeof email !== 'string') {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }

    const normalizedEmail = email.toLowerCase().trim();

    if (!EMAIL_REGEX.test(normalizedEmail)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    // Check if already on waitlist
    const existing = await prisma.waitlistEntry.findUnique({
      where: { email: normalizedEmail },
    });

    if (existing) {
      // Don't reveal that email exists, just return success
      return NextResponse.json({ success: true, message: "You're on the list!" });
    }

    // Add to waitlist
    await prisma.waitlistEntry.create({
      data: {
        email: normalizedEmail,
        source: source || null,
      },
    });

    return NextResponse.json({ 
      success: true, 
      message: "You're on the list! We'll be in touch soon." 
    });

  } catch (error) {
    console.error('Waitlist error:', error);
    return NextResponse.json(
      { error: 'Failed to join waitlist' },
      { status: 500 }
    );
  }
}
