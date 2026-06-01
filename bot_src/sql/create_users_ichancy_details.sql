-- Create the users_ichancy_details table for storing iChancy account data
-- Run this SQL in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.users_ichancy_details (
    id BIGSERIAL PRIMARY KEY,
    telegram_id TEXT NOT NULL UNIQUE,
    username TEXT,
    email TEXT,
    password TEXT,
    player_id TEXT DEFAULT '0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.users_ichancy_details ENABLE ROW LEVEL SECURITY;

-- Create policy to allow the service role (bot) to do everything
CREATE POLICY "Service role can do everything on users_ichancy_details"
ON public.users_ichancy_details
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- Create index on telegram_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_ichancy_details_telegram_id
ON public.users_ichancy_details (telegram_id);

-- Add comment
COMMENT ON TABLE public.users_ichancy_details IS 'Stores iChancy account details linked to Telegram users';
