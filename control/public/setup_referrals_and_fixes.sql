-- =====================================================
-- 🔥 إصلاح شامل: جدول referrals + كل الإضافات
-- =====================================================

-- 1️⃣ إنشاء جدول referrals المفقود
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

-- فهارس للسرعة
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id);

-- 2️⃣ RLS للجدول
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS referrals_all ON referrals;
CREATE POLICY referrals_all ON referrals FOR ALL USING (true) WITH CHECK (true);

-- 3️⃣ إضافة أعمدة الإحالات للمستخدمين
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS referral_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_referrals integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS referral_code text UNIQUE;

-- 4️⃣ إنشاء أكواد إحالة فريدة للمستخدمين الموجودين
UPDATE users 
SET referral_code = 'REF' || telegram_id::text
WHERE referral_code IS NULL;

-- 5️⃣ إضافة أعمدة البونص للإيداعات
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS bonus_amount integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS bonus_percentage decimal(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_amount decimal(15,2);

-- 6️⃣ إضافة نسبة البونص للمحافظ
ALTER TABLE wallets 
ADD COLUMN IF NOT EXISTS bonus_percentage decimal(5,2) DEFAULT 0;

-- 7️⃣ إنشاء جدول أكواد الهدايا
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

-- 8️⃣ إنشاء جدول الرسائل الجماعية
CREATE TABLE IF NOT EXISTS broadcast_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message text NOT NULL,
    sent_count integer DEFAULT 0,
    failed_count integer DEFAULT 0,
    status text DEFAULT 'pending',
    created_at timestamptz DEFAULT now(),
    completed_at timestamptz
);

ALTER TABLE broadcast_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS broadcast_all ON broadcast_messages;
CREATE POLICY broadcast_all ON broadcast_messages FOR ALL USING (true) WITH CHECK (true);

-- 9️⃣ تفعيل Realtime للجميع
ALTER PUBLICATION supabase_realtime ADD TABLE referrals;
ALTER PUBLICATION supabase_realtime ADD TABLE gift_codes;
ALTER PUBLICATION supabase_realtime ADD TABLE broadcast_messages;

-- 🔟 تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ جميع الجداول والأعمدة تم إنشاؤها بنجاح!' as result;
