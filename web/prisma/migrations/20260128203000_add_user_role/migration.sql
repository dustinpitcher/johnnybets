-- Add role column to users table
ALTER TABLE "users" ADD COLUMN "role" TEXT NOT NULL DEFAULT 'user';

-- Add contextSnapshot to message_feedbacks
ALTER TABLE "message_feedbacks" ADD COLUMN IF NOT EXISTS "context_snapshot" JSONB;
