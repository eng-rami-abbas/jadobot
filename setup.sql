-- JADO BOT - Supabase Database Setup
-- Run this in Supabase SQL Editor

-- Enable Row Level Security
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS deposits ENABLE ROW LEVEL SECURITY;

-- Create spins table
CREATE TABLE IF NOT EXISTS spins (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    spin_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create spin_results table
CREATE TABLE IF NOT EXISTS spin_results (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    prize TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create free_spins table
CREATE TABLE IF NOT EXISTS free_spins (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    remaining INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create bonus_rewards table
CREATE TABLE IF NOT EXISTS bonus_rewards (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bonus_percent NUMERIC DEFAULT 5,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create premium_rewards table
CREATE TABLE IF NOT EXISTS premium_rewards (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_spins_user_date ON spins(user_id, spin_date);
CREATE INDEX IF NOT EXISTS idx_spin_results_user ON spin_results(user_id);
CREATE INDEX IF NOT EXISTS idx_spin_results_created ON spin_results(created_at);
CREATE INDEX IF NOT EXISTS idx_free_spins_user ON free_spins(user_id);
CREATE INDEX IF NOT EXISTS idx_bonus_rewards_user ON bonus_rewards(user_id);
CREATE INDEX IF NOT EXISTS idx_premium_rewards_user ON premium_rewards(user_id);

-- Row Level Security Policies

-- Spins: Users can only see their own spins
CREATE POLICY "Users can view own spins" ON spins
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Spin results: Users can only see their own results
CREATE POLICY "Users can view own results" ON spin_results
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Free spins: Users can only see their own
CREATE POLICY "Users can view own free spins" ON free_spins
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Bonus rewards: Users can only see their own
CREATE POLICY "Users can view own bonuses" ON bonus_rewards
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Premium rewards: Users can only see their own
CREATE POLICY "Users can view own premiums" ON premium_rewards
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Create RPC function for secure spin result (fallback if Edge Function not used)
CREATE OR REPLACE FUNCTION get_spin_result(p_user_id BIGINT)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result TEXT;
    v_random NUMERIC;
    v_has_deposit BOOLEAN;
    v_has_daily_spin BOOLEAN;
    v_free_spins INTEGER;
    v_today DATE;
BEGIN
    v_today := CURRENT_DATE;

    -- Check deposit
    SELECT EXISTS(SELECT 1 FROM deposits WHERE user_id = p_user_id LIMIT 1)
    INTO v_has_deposit;

    IF NOT v_has_deposit THEN
        RAISE EXCEPTION 'No deposit found';
    END IF;

    -- Check daily spin
    SELECT NOT EXISTS(SELECT 1 FROM spins WHERE user_id = p_user_id AND spin_date = v_today LIMIT 1)
    INTO v_has_daily_spin;

    -- Check free spins
    SELECT COALESCE(remaining, 0) INTO v_free_spins
    FROM free_spins WHERE user_id = p_user_id;

    IF NOT v_has_daily_spin AND (v_free_spins IS NULL OR v_free_spins <= 0) THEN
        RAISE EXCEPTION 'No spins remaining';
    END IF;

    -- Generate random result using pg_crypto
    v_random := random();

    -- Weighted random selection
    IF v_random <= 0.15 THEN
        v_result := '10000';
    ELSIF v_random <= 0.25 THEN
        v_result := '20000';
    ELSIF v_random <= 0.50 THEN
        v_result := 'حظ أوفر';
    ELSIF v_random <= 0.55 THEN
        v_result := 'Telegram Premium';
    ELSIF v_random <= 0.60 THEN
        v_result := '50000';
    ELSIF v_random <= 0.75 THEN
        v_result := 'Bonus 5%';
    ELSIF v_random <= 0.90 THEN
        v_result := 'حظ أوفر';
    ELSE
        v_result := 'إعادة تدوير';
    END IF;

    RETURN v_result;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_spin_result(BIGINT) TO anon;
GRANT EXECUTE ON FUNCTION get_spin_result(BIGINT) TO authenticated;

-- Create function to get today's stats (for admin)
CREATE OR REPLACE FUNCTION get_today_stats()
RETURNS TABLE(
    total_spins BIGINT,
    unique_players BIGINT,
    total_prizes BIGINT,
    premium_count BIGINT,
    bonus_count BIGINT,
    free_spins_given BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM spins WHERE spin_date = CURRENT_DATE),
        (SELECT COUNT(DISTINCT user_id) FROM spins WHERE spin_date = CURRENT_DATE),
        (SELECT COALESCE(SUM(CASE WHEN prize IN ('10000','20000','50000') THEN prize::BIGINT ELSE 0 END), 0) 
         FROM spin_results WHERE created_at >= CURRENT_DATE),
        (SELECT COUNT(*) FROM spin_results WHERE prize = 'Telegram Premium' AND created_at >= CURRENT_DATE),
        (SELECT COUNT(*) FROM spin_results WHERE prize = 'Bonus 5%' AND created_at >= CURRENT_DATE),
        (SELECT COUNT(*) FROM spin_results WHERE prize = 'إعادة تدوير' AND created_at >= CURRENT_DATE);
END;
$$;

GRANT EXECUTE ON FUNCTION get_today_stats() TO anon;
GRANT EXECUTE ON FUNCTION get_today_stats() TO authenticated;
