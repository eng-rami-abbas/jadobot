-- ===== JADO BOT - Supabase Database Schema =====

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===== Users Table =====
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT UNIQUE NOT NULL,           -- Telegram user ID
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    balance BIGINT DEFAULT 0,                  -- User balance
    spins_today INTEGER DEFAULT 0,             -- Spins used today
    max_spins_per_day INTEGER DEFAULT 1,     -- Max spins per day
    last_spin_date DATE,                      -- Last spin date
    deposits_today INTEGER DEFAULT 0,          -- Deposits count today
    last_deposit_date DATE,                   -- Last deposit date
    total_deposits BIGINT DEFAULT 0,          -- Total deposited amount
    pending_bonus INTEGER,                    -- Pending bonus percentage
    lucky_charms INTEGER DEFAULT 0,          -- Lucky charms count
    pending_premium BOOLEAN DEFAULT FALSE,     -- Pending Telegram Premium
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===== Deposits Table =====
CREATE TABLE IF NOT EXISTS deposits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    payment_method TEXT,                       -- e.g., 'crypto', 'bank', etc.
    status TEXT DEFAULT 'pending',            -- pending, completed, failed
    transaction_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ===== Wheel Spins Table =====
CREATE TABLE IF NOT EXISTS wheel_spins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    result_type TEXT NOT NULL,                 -- money, lucky, premium, bonus, respins
    result_label TEXT NOT NULL,                -- e.g., '10000', 'حظ أوفر'
    result_value BIGINT,                       -- Numeric value if applicable
    balance_before BIGINT,
    balance_after BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===== Transactions/History Table =====
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    type TEXT NOT NULL,                        -- deposit, spin_win, bonus, withdrawal
    amount BIGINT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===== Indexes =====
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits(user_id);
CREATE INDEX IF NOT EXISTS idx_wheel_spins_user_id ON wheel_spins(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_wheel_spins_created ON wheel_spins(created_at);

-- ===== Updated At Trigger =====
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ===== Reset Daily Spins Function (Run via cron) =====
CREATE OR REPLACE FUNCTION reset_daily_spins()
RETURNS void AS $$
BEGIN
    UPDATE users 
    SET spins_today = 0, 
        deposits_today = 0,
        last_spin_date = NULL,
        last_deposit_date = NULL
    WHERE last_spin_date < CURRENT_DATE 
       OR last_deposit_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- ===== RLS Policies =====
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE deposits ENABLE ROW LEVEL SECURITY;
ALTER TABLE wheel_spins ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Users can only read their own data
CREATE POLICY "Users can read own data" ON users
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Users can only update their own data
CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (auth.uid()::text = user_id::text);

-- Deposits policies
CREATE POLICY "Users can read own deposits" ON deposits
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Wheel spins policies
CREATE POLICY "Users can read own spins" ON wheel_spins
    FOR SELECT USING (auth.uid()::text = user_id::text);

-- Transactions policies
CREATE POLICY "Users can read own transactions" ON transactions
    FOR SELECT USING (auth.uid()::text = user_id::text);
