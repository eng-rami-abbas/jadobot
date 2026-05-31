-- 🔥 إضافة عمود header_text للمحافظ
-- النص الأول الذي يظهر قبل العنوان عند اختيار المحفظة

-- إضافة العمود إذا لم يكن موجوداً
ALTER TABLE wallets 
ADD COLUMN IF NOT EXISTS header_text TEXT DEFAULT '';

-- تحديث description
COMMENT ON COLUMN wallets.header_text IS 'النص الأول الذي يظهر قبل العنوان عند اختيار المحفظة في البوت';
