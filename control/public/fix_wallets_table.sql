-- ============================================
-- إصلاح جدول المحافظ - خطوة بخطوة
-- ============================================

-- الخطوة 1: إضافة الأعمدة المفقودة (بدون تحديثات معقدة)
ALTER TABLE wallets 
ADD COLUMN IF NOT EXISTS key text,
ADD COLUMN IF NOT EXISTS wallet_number text,
ADD COLUMN IF NOT EXISTS address text,
ADD COLUMN IF NOT EXISTS title text DEFAULT '',
ADD COLUMN IF NOT EXISTS image_url text DEFAULT '',
ADD COLUMN IF NOT EXISTS emoji text DEFAULT '💳';

-- الخطوة 2: إنشاء قيم key من اسم المحفظة الموجود
UPDATE wallets 
SET key = LOWER(REPLACE(REPLACE(name, ' ', '_'), '-', '_'))
WHERE key IS NULL OR key = '';

-- الخطوة 3: نسخ البيانات الموجودة - إذا كان هناك عمود address أصلي
-- إذا كان العمود القديم يحتوي على الرقم، انسخه للأعمدة الجديدة
UPDATE wallets 
SET wallet_number = COALESCE(wallet_number, name),
    address = COALESCE(address, wallet_number, name)
WHERE wallet_number IS NULL;

-- الخطوة 4: إضافة قيود UNIQUE على key (بعد التأكد من عدم وجود قيم مكررة)
-- أولاً احذف القيم المكررة إن وجدت
DELETE FROM wallets 
WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY key ORDER BY created_at) as rn
        FROM wallets
        WHERE key IS NOT NULL
    ) t WHERE rn > 1
);

-- ثم أضف القيد
ALTER TABLE wallets ADD CONSTRAINT wallets_key_unique UNIQUE (key);

-- ============================================
-- التحقق من البيانات
-- ============================================
SELECT id, name, key, wallet_number, address, title, is_active FROM wallets;
