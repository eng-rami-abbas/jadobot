-- =====================================================
-- ⏰ إضافة عمود تاريخ الانتهاء لجدول أكواد الهدايا
-- =====================================================

-- إضافة عمود expires_at
ALTER TABLE gift_codes 
ADD COLUMN IF NOT EXISTS expires_at timestamptz;

-- تحديث Schema Cache
NOTIFY pgrst, 'reload schema';

SELECT '✅ Added expires_at column to gift_codes' as status;
