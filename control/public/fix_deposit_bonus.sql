-- =====================================================
-- 🔥 إضافة نسبة البونص للإيداعات
-- =====================================================

-- إضافة أعمدة البونص لجدول transactions
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS bonus_amount integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS bonus_percentage decimal(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_amount decimal(15,2);

-- إضافة عمود البونص لجدول wallets
ALTER TABLE wallets 
ADD COLUMN IF NOT EXISTS bonus_percentage decimal(5,2) DEFAULT 0;

-- تحديث schema cache
NOTIFY pgrst, 'reload schema';

-- =====================================================
-- ✅ التحقق
-- =====================================================
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'transactions' 
AND column_name IN ('bonus_amount', 'bonus_percentage', 'total_amount');

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'wallets' 
AND column_name = 'bonus_percentage';
