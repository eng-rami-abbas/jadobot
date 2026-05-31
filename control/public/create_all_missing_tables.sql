-- =====================================================
-- 🔥 إنشاء جميع الجداول المفقودة
-- =====================================================

-- 1️⃣ جدول أكواد الهدايا
CREATE TABLE IF NOT EXISTS gift_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL,
    amount integer NOT NULL,
    is_used boolean DEFAULT false,
    used_by bigint REFERENCES users(telegram_id),
    used_at timestamptz,
    notes text,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gift_codes_code ON gift_codes(code);
CREATE INDEX IF NOT EXISTS idx_gift_codes_used ON gift_codes(is_used);
ALTER TABLE gift_codes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS gift_codes_all ON gift_codes;
CREATE POLICY gift_codes_all ON gift_codes FOR ALL USING (true) WITH CHECK (true);

-- 2️⃣ جدول الرسائل الجماعية
CREATE TABLE IF NOT EXISTS broadcast_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message text NOT NULL,
    sent_count integer DEFAULT 0,
    failed_count integer DEFAULT 0,
    status text DEFAULT 'pending',
    created_at timestamptz DEFAULT now(),
    completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_broadcast_status ON broadcast_messages(status);
ALTER TABLE broadcast_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS broadcast_all ON broadcast_messages;
CREATE POLICY broadcast_all ON broadcast_messages FOR ALL USING (true) WITH CHECK (true);

-- 3️⃣ جدول الإحالات
CREATE TABLE IF NOT EXISTS referrals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id bigint NOT NULL,
    referred_id bigint NOT NULL,
    referral_code text,
    status text DEFAULT 'active',
    reward_amount integer DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id);
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS referrals_all ON referrals;
CREATE POLICY referrals_all ON referrals FOR ALL USING (true) WITH CHECK (true);

-- 4️⃣ تفعيل Realtime للجميع
ALTER PUBLICATION supabase_realtime ADD TABLE gift_codes;
ALTER PUBLICATION supabase_realtime ADD TABLE broadcast_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE referrals;

-- 5️⃣ تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ جميع الجداول تم إنشاؤها' as result;
