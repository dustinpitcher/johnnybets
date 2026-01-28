/**
 * Email Service using Azure Communication Services
 * 
 * Provides transactional email functionality for:
 * - Password reset emails
 * - Invite notifications for waitlist users
 * - Future: Marketing emails via email agent
 */
import { EmailClient, EmailMessage } from '@azure/communication-email';

// Lazy initialization of email client
let emailClient: EmailClient | null = null;

function getEmailClient(): EmailClient {
  if (!emailClient) {
    const connectionString = process.env.AZURE_COMMUNICATION_CONNECTION_STRING;
    if (!connectionString) {
      throw new Error('AZURE_COMMUNICATION_CONNECTION_STRING environment variable is not set');
    }
    emailClient = new EmailClient(connectionString);
  }
  return emailClient;
}

// Get sender address from environment or use custom domain
function getSenderAddress(): string {
  return process.env.EMAIL_FROM || 'noreply@johnnybets.ai';
}

// Get the base URL for email links
function getBaseUrl(): string {
  return process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_APP_URL || 'https://johnnybets.com';
}

/**
 * Send an email using Azure Communication Services
 */
async function sendEmail(message: EmailMessage): Promise<void> {
  const client = getEmailClient();
  
  try {
    const poller = await client.beginSend(message);
    const result = await poller.pollUntilDone();
    
    if (result.status !== 'Succeeded') {
      throw new Error(`Email send failed with status: ${result.status}`);
    }
    
    console.log(`Email sent successfully to ${message.recipients.to?.map(r => r.address).join(', ')}`);
  } catch (error) {
    console.error('Failed to send email:', error);
    throw error;
  }
}

/**
 * Send a password reset email
 */
export async function sendPasswordResetEmail(to: string, resetToken: string): Promise<void> {
  const baseUrl = getBaseUrl();
  const resetUrl = `${baseUrl}/auth/reset-password?token=${resetToken}`;
  
  const message: EmailMessage = {
    senderAddress: getSenderAddress(),
    recipients: {
      to: [{ address: to }],
    },
    content: {
      subject: 'Reset your JohnnyBets password',
      plainText: `You requested a password reset for your JohnnyBets account.

Click the link below to reset your password:
${resetUrl}

This link will expire in 1 hour.

If you didn't request this password reset, you can safely ignore this email.

- The JohnnyBets Team`,
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
    <h1 style="color: #00ff88; margin: 0; font-size: 28px;">JohnnyBets</h1>
  </div>
  
  <h2 style="color: #1a1a2e; margin-bottom: 20px;">Reset Your Password</h2>
  
  <p>You requested a password reset for your JohnnyBets account.</p>
  
  <p>Click the button below to set a new password:</p>
  
  <div style="text-align: center; margin: 30px 0;">
    <a href="${resetUrl}" style="background: #00ff88; color: #1a1a2e; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">Reset Password</a>
  </div>
  
  <p style="color: #666; font-size: 14px;">This link will expire in 1 hour.</p>
  
  <p style="color: #666; font-size: 14px;">If you didn't request this password reset, you can safely ignore this email.</p>
  
  <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
  
  <p style="color: #999; font-size: 12px; text-align: center;">
    &copy; ${new Date().getFullYear()} JohnnyBets. All rights reserved.
  </p>
</body>
</html>
      `.trim(),
    },
  };
  
  await sendEmail(message);
}

/**
 * Send an invite notification to a waitlist user
 */
export async function sendInviteNotification(to: string, inviteCode: string): Promise<void> {
  const baseUrl = getBaseUrl();
  const signupUrl = `${baseUrl}/auth/signin?inviteCode=${inviteCode}`;
  
  const message: EmailMessage = {
    senderAddress: getSenderAddress(),
    recipients: {
      to: [{ address: to }],
    },
    content: {
      subject: "You're invited to JohnnyBets!",
      plainText: `Great news! Your spot on the JohnnyBets waitlist has come through.

Your exclusive invite code: ${inviteCode}

Sign up now: ${signupUrl}

This invite code is limited, so don't wait too long to claim your spot!

- The JohnnyBets Team`,
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
    <h1 style="color: #00ff88; margin: 0; font-size: 28px;">JohnnyBets</h1>
  </div>
  
  <h2 style="color: #1a1a2e; margin-bottom: 20px;">You're In! 🎉</h2>
  
  <p>Great news! Your spot on the JohnnyBets waitlist has come through.</p>
  
  <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 25px 0;">
    <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">Your exclusive invite code:</p>
    <p style="font-family: monospace; font-size: 24px; font-weight: bold; color: #1a1a2e; margin: 0; letter-spacing: 2px;">${inviteCode}</p>
  </div>
  
  <div style="text-align: center; margin: 30px 0;">
    <a href="${signupUrl}" style="background: #00ff88; color: #1a1a2e; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">Create Your Account</a>
  </div>
  
  <p style="color: #666; font-size: 14px;">This invite code is limited, so don't wait too long to claim your spot!</p>
  
  <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
  
  <p style="color: #999; font-size: 12px; text-align: center;">
    &copy; ${new Date().getFullYear()} JohnnyBets. All rights reserved.
  </p>
</body>
</html>
      `.trim(),
    },
  };
  
  await sendEmail(message);
}

/**
 * Send a generic email (for future email agent use)
 */
export async function sendGenericEmail(
  to: string[],
  subject: string,
  htmlBody: string,
  plainTextBody?: string
): Promise<void> {
  const message: EmailMessage = {
    senderAddress: getSenderAddress(),
    recipients: {
      to: to.map(address => ({ address })),
    },
    content: {
      subject,
      html: htmlBody,
      plainText: plainTextBody || htmlBody.replace(/<[^>]*>/g, ''), // Strip HTML for plain text fallback
    },
  };
  
  await sendEmail(message);
}
