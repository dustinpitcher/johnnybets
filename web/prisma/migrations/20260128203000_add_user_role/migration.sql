-- Add role column to users table
ALTER TABLE "users" ADD COLUMN "role" TEXT NOT NULL DEFAULT 'user';

-- Create message_feedbacks table if it doesn't exist
CREATE TABLE IF NOT EXISTS "message_feedbacks" (
    "id" TEXT NOT NULL,
    "session_id" TEXT NOT NULL,
    "message_index" INTEGER NOT NULL,
    "feedback_type" TEXT NOT NULL,
    "comment" TEXT,
    "context_snapshot" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "message_feedbacks_pkey" PRIMARY KEY ("id")
);

-- Create index on session_id if table was just created
CREATE INDEX IF NOT EXISTS "message_feedbacks_session_id_idx" ON "message_feedbacks"("session_id");

-- Add foreign key if it doesn't exist (ignore error if already exists)
DO $$
BEGIN
    ALTER TABLE "message_feedbacks" ADD CONSTRAINT "message_feedbacks_session_id_fkey" 
        FOREIGN KEY ("session_id") REFERENCES "sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;
