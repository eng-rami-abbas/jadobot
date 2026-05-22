-- =====================================================
-- 🔥 إصلاح أعمدة جدول gift_codes المفقودة
-- =====================================================

-- إضافة الأعمدة المفقودة
ALTER TABLE gift_codes 
ADD COLUMN IF NOT EXISTS is_used boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS used_by bigint REFERENCES users(telegram_id),
ADD COLUMN IF NOT EXISTS used_at timestamptz,
ADD COLUMN IF NOT EXISTS notes text;

-- إنشاء الفهارس إذا لم تكن موجودة
CREATE INDEX IF NOT EXISTS idx_gift_codes_code ON gift_codes(code);
CREATE INDEX IF NOT EXISTS idx_gift_codes_used ON gift_codes(is_used);

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

-- التحقق
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'gift_codes';
