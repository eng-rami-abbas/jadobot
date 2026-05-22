-- =====================================================
-- 🎨 إضافة عمود لون الزر للمحافظ
-- =====================================================

-- إضافة العمود (إذا غير موجود)
ALTER TABLE wallets 
ADD COLUMN IF NOT EXISTS button_color text DEFAULT '#3b82f6';

-- تحديث القيم الافتراضية للمحافظ الموجودة
UPDATE wallets 
SET button_color = '#3b82f6' 
WHERE button_color IS NULL;

-- تحديث Schema Cache
NOTIFY pgrst, 'reload schema';

SELECT '✅ button_color column added to wallets' as status;
