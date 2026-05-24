-- ============================================================
-- JADO BOT — Roulette Web App (Supabase)
-- Run in Supabase SQL Editor
-- ============================================================

-- Extra spin counter (from "إعادة تدوير" prize)
ALTER TABLE wheel_spins
  ADD COLUMN IF NOT EXISTS extra_spins integer DEFAULT 0;

ALTER TABLE wheel_spins
  ADD COLUMN IF NOT EXISTS pending_bonus_percent numeric DEFAULT 0;

-- Daily spin log
CREATE TABLE IF NOT EXISTS spins (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    spin_date date NOT NULL,
    is_bonus_spin boolean DEFAULT false,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spins_telegram_date ON spins(telegram_id, spin_date);

-- Immutable results (server authority)
CREATE TABLE IF NOT EXISTS spin_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    spin_id uuid REFERENCES spins(id) ON DELETE CASCADE,
    telegram_id bigint NOT NULL,
    segment_index smallint NOT NULL CHECK (segment_index >= 0 AND segment_index < 8),
    prize_type text NOT NULL,
    prize_code text NOT NULL,
    prize_payload jsonb DEFAULT '{}'::jsonb,
    target_angle numeric NOT NULL,
    claimed boolean DEFAULT false,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spin_results_telegram ON spin_results(telegram_id);

-- Pending deposit bonus from wheel
CREATE TABLE IF NOT EXISTS bonus_rewards (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    percent numeric NOT NULL,
    used boolean DEFAULT false,
    spin_result_id uuid REFERENCES spin_results(id),
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bonus_rewards_active ON bonus_rewards(telegram_id, used);

-- Telegram Premium fulfillment queue
CREATE TABLE IF NOT EXISTS telegram_premium_rewards (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    status text DEFAULT 'pending' CHECK (status IN ('pending', 'claimed', 'cancelled')),
    spin_result_id uuid REFERENCES spin_results(id),
    notes text DEFAULT '',
    created_at timestamptz DEFAULT now()
);

-- Deposit mirror (optional analytics; main deposits live in transactions)
CREATE TABLE IF NOT EXISTS roulette_deposits (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    amount_syp numeric NOT NULL,
    deposit_date date NOT NULL,
    transaction_id uuid,
    created_at timestamptz DEFAULT now()
);

ALTER TABLE spins ENABLE ROW LEVEL SECURITY;
ALTER TABLE spin_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE bonus_rewards ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_premium_rewards ENABLE ROW LEVEL SECURITY;
ALTER TABLE roulette_deposits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS spins_all ON spins;
CREATE POLICY spins_all ON spins FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS spin_results_all ON spin_results;
CREATE POLICY spin_results_all ON spin_results FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS bonus_rewards_all ON bonus_rewards;
CREATE POLICY bonus_rewards_all ON bonus_rewards FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS premium_rewards_all ON telegram_premium_rewards;
CREATE POLICY premium_rewards_all ON telegram_premium_rewards FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS roulette_deposits_all ON roulette_deposits;
CREATE POLICY roulette_deposits_all ON roulette_deposits FOR ALL USING (true) WITH CHECK (true);

NOTIFY pgrst, 'reload schema';
