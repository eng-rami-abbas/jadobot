-- =====================================================
-- 🔥 إصلاح سريع - حذف وإعادة بناء جدول wallets
-- ⚠️ سيحذف كل البيانات الموجودة
-- =====================================================

-- حذف الجدول وكل البيانات
DROP TABLE IF EXISTS wallets CASCADE;

-- إنشاء جديد بدون قيود
CREATE TABLE wallets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL DEFAULT 'محفظة جديدة',
    key text UNIQUE NOT NULL DEFAULT 'wallet_' || extract(epoch from now())::text,
    wallet_number text NOT NULL DEFAULT '0',
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

-- فهارس
CREATE INDEX idx_wallets_key ON wallets(key);

-- ⚠️ مؤقتاً - مفتوح للجميع
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
CREATE POLICY wallets_open ON wallets FOR ALL USING (true) WITH CHECK (true);

-- Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE wallets;

-- إضافة محفظة افتراضية
INSERT INTO wallets (name, key, wallet_number, title, emoji) 
VALUES ('بنك Bemo', 'bemo', '1234567890', 'بنك بيمو', '🏦');

NOTIFY pgrst, 'reload schema';

SELECT '✅ تم إعادة بناء جدول wallets - جرب الآن' as result;
