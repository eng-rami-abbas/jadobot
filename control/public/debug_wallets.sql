-- =====================================================
-- 🔥 فحص وإصلاح جدول المحافظ
-- =====================================================

-- 1️⃣ فحص هيكل الجدول
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'wallets'
ORDER BY ordinal_position;

-- 2️⃣ فحص RLS Policies
SELECT policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'wallets';

-- 3️⃣ حذف وإعادة إنشاء الجدول إذا فيه مشكلة (⚠️ احذف البيانات)
DROP TABLE IF EXISTS wallets CASCADE;

CREATE TABLE wallets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    key text UNIQUE NOT NULL,
    wallet_number text NOT NULL,
    address text DEFAULT '',
    title text DEFAULT '',
    image_url text DEFAULT '',
    emoji text DEFAULT '💳',
    message_template text DEFAULT '',
    is_active boolean DEFAULT true,
    sort_order integer DEFAULT 0,
    bonus_percentage decimal(5,2) DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 4️⃣ فهارس
CREATE INDEX idx_wallets_key ON wallets(key);
CREATE INDEX idx_wallets_active ON wallets(is_active);

-- 5️⃣ RLS - مفتوح للجميع للتجربة
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS wallets_all ON wallets;
CREATE POLICY wallets_all ON wallets FOR ALL USING (true) WITH CHECK (true);

-- 6️⃣ Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE wallets;

-- 7️⃣ تحديث Schema
NOTIFY pgrst, 'reload schema';

-- 8️⃣ إضافة محفظة تجريبية
INSERT INTO wallets (name, key, wallet_number, title, emoji, is_active, sort_order)
VALUES ('بنك تجريبي', 'test_bank', '123456789', 'بنك تجريبي', '🏦', true, 1);

SELECT '✅ تم إعادة إنشاء جدول المحافظ بنجاح' as result;
