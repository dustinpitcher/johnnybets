/**
 * Test script for Azure Communication Services Email
 * 
 * Run with: npx tsx scripts/test-email.ts your-email@example.com
 */
import { EmailClient } from '@azure/communication-email';

const connectionString = process.env.AZURE_COMMUNICATION_CONNECTION_STRING;
const senderAddress = process.env.EMAIL_FROM || 'DoNotReply@40734439-2eb5-4235-a8f0-1fd78cf1b04f.azurecomm.net';

async function testEmail(toAddress: string) {
  if (!connectionString) {
    console.error('ERROR: AZURE_COMMUNICATION_CONNECTION_STRING not set');
    console.log('Make sure to run with: npx dotenv -e .env.local -- npx tsx scripts/test-email.ts <email>');
    process.exit(1);
  }

  console.log('Configuration:');
  console.log('  Connection string:', connectionString.substring(0, 50) + '...');
  console.log('  Sender:', senderAddress);
  console.log('  To:', toAddress);
  console.log('');

  const client = new EmailClient(connectionString);

  const message = {
    senderAddress,
    recipients: {
      to: [{ address: toAddress }],
    },
    content: {
      subject: 'JohnnyBets Email Test',
      plainText: 'This is a test email from JohnnyBets. If you received this, email is working!',
      html: '<h1>JohnnyBets Email Test</h1><p>This is a test email. If you received this, email is working!</p>',
    },
  };

  console.log('Sending email...');
  
  try {
    const poller = await client.beginSend(message);
    console.log('  Message ID:', poller.getOperationState().id);
    
    const result = await poller.pollUntilDone();
    console.log('  Status:', result.status);
    
    if (result.status === 'Succeeded') {
      console.log('\n✅ Email sent successfully!');
    } else {
      console.log('\n❌ Email failed with status:', result.status);
      console.log('  Error:', result.error);
    }
  } catch (error: any) {
    console.error('\n❌ Error sending email:');
    console.error('  Message:', error.message);
    if (error.code) console.error('  Code:', error.code);
    if (error.details) console.error('  Details:', JSON.stringify(error.details, null, 2));
  }
}

const toEmail = process.argv[2];
if (!toEmail) {
  console.log('Usage: npx dotenv -e .env.local -- npx tsx scripts/test-email.ts <your-email@example.com>');
  process.exit(1);
}

testEmail(toEmail);
