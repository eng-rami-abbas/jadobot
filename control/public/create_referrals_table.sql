-- =====================================================
-- 🔥 إنشاء جدول الإحالات (referrals)
-- =====================================================

-- إنشاء الجدول
CREATE TABLE IF NOT EXISTS referrals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id bigint NOT NULL REFERENCES users(telegram_id),
    referred_id bigint NOT NULL REFERENCES users(telegram_id),
    referral_code text,
    status text DEFAULT 'active',
    reward_amount integer DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- إضافة فهارس
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code);

-- تفعيل RLS
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;

-- سياسات RLS
DROP POLICY IF EXISTS referrals_select_policy ON referrals;
DROP POLICY IF EXISTS referrals_insert_policy ON referrals;
DROP POLICY IF EXISTS referrals_update_policy ON referrals;
DROP POLICY IF EXISTS referrals_delete_policy ON referrals;

CREATE POLICY referrals_select_policy ON referrals
    FOR SELECT USING (true);

CREATE POLICY referrals_insert_policy ON referrals
    FOR INSERT WITH CHECK (true);

CREATE POLICY referrals_update_policy ON referrals
    FOR UPDATE USING (true);

CREATE POLICY referrals_delete_policy ON referrals
    FOR DELETE USING (true);

-- تفعيل Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE referrals;

-- تحديث Schema Cache
NOTIFY pgrst, 'reload schema';

-- التحقق
SELECT ' referrals table created successfully ' as status;
