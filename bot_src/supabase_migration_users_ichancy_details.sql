-- ============================================================
-- SQL Migration: Create users_ichancy_details table in Supabase
-- ============================================================
-- Run this SQL in Supabase SQL Editor (https://supabase.com/dashboard)
-- This table stores iChancy account details for each Telegram user
-- ============================================================

-- Create the table
CREATE TABLE IF NOT EXISTS public.users_ichancy_details (
    id BIGSERIAL PRIMARY KEY,
    telegram_id TEXT NOT NULL,
    username TEXT NOT NULL,
    email TEXT,
    password TEXT,
    player_id TEXT DEFAULT '0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add unique constraint on telegram_id (one iChancy account per Telegram user)
ALTER TABLE public.users_ichancy_details 
    ADD CONSTRAINT users_ichancy_details_telegram_id_key UNIQUE (telegram_id);

-- Enable Row Level Security
ALTER TABLE public.users_ichancy_details ENABLE ROW LEVEL SECURITY;

-- Create policy: allow service role full access (used by bot with service_role key)
CREATE POLICY "Service role can do everything on users_ichancy_details"
    ON public.users_ichancy_details
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_ichancy_details_telegram_id 
    ON public.users_ichancy_details (telegram_id);

-- Also add ichancy columns to users table as fallback storage
-- (These columns are used by the fallback functions in supabase_integration.py)
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS ichancy_username TEXT;
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS ichancy_email TEXT;
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS ichancy_password TEXT;
ALTER TABLE public.users 
    ADD COLUMN IF NOT EXISTS ichancy_player_id TEXT;

-- ============================================================
-- AFTER RUNNING THIS SQL:
-- 1. The bot will be able to save iChancy account details
-- 2. The keyboard will show correct buttons after account creation
-- 3. Account info will persist across bot restarts
-- ============================================================
