/**
 * Simple encryption utilities for API keys at rest.
 * 
 * In production, consider using a proper secrets manager (e.g., Azure Key Vault).
 * This provides basic protection for stored credentials.
 */
import crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16;
const TAG_LENGTH = 16;

// Use NEXTAUTH_SECRET as encryption key (or a dedicated ENCRYPTION_KEY)
function getEncryptionKey(): Buffer {
  const secret = process.env.ENCRYPTION_KEY || process.env.NEXTAUTH_SECRET;
  if (!secret) {
    throw new Error('ENCRYPTION_KEY or NEXTAUTH_SECRET must be set');
  }
  // Derive a 32-byte key from the secret
  return crypto.createHash('sha256').update(secret).digest();
}

/**
 * Encrypt a string value
 */
export function encrypt(plaintext: string): string {
  const key = getEncryptionKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
  
  let encrypted = cipher.update(plaintext, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  
  const tag = cipher.getAuthTag();
  
  // Format: iv:tag:encrypted
  return `${iv.toString('hex')}:${tag.toString('hex')}:${encrypted}`;
}

/**
 * Decrypt an encrypted string value
 */
export function decrypt(encryptedValue: string): string {
  const key = getEncryptionKey();
  
  const parts = encryptedValue.split(':');
  if (parts.length !== 3) {
    throw new Error('Invalid encrypted value format');
  }
  
  const [ivHex, tagHex, encrypted] = parts;
  const iv = Buffer.from(ivHex, 'hex');
  const tag = Buffer.from(tagHex, 'hex');
  
  const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
  decipher.setAuthTag(tag);
  
  let decrypted = decipher.update(encrypted, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  
  return decrypted;
}

/**
 * Mask an API key for display (show first 4 and last 4 chars)
 */
export function maskApiKey(key: string): string {
  if (key.length <= 8) {
    return '****';
  }
  return `${key.slice(0, 4)}...${key.slice(-4)}`;
}
