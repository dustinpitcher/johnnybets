-- AlterTable: Add invite_code_id to users
ALTER TABLE "users" ADD COLUMN "invite_code_id" TEXT;

-- CreateTable: waitlist_entries
CREATE TABLE "waitlist_entries" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "source" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "waitlist_entries_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "waitlist_entries_email_key" ON "waitlist_entries"("email");

-- CreateTable: invite_codes
CREATE TABLE "invite_codes" (
    "id" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "max_uses" INTEGER NOT NULL DEFAULT 1,
    "use_count" INTEGER NOT NULL DEFAULT 0,
    "expires_at" TIMESTAMP(3),
    "created_by" TEXT,
    "note" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "invite_codes_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "invite_codes_code_key" ON "invite_codes"("code");

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_invite_code_id_fkey" FOREIGN KEY ("invite_code_id") REFERENCES "invite_codes"("id") ON DELETE SET NULL ON UPDATE CASCADE;
