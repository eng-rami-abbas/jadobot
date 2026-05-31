-- =====================================================
-- 🔥 تحديث Schema Cache
-- =====================================================

-- 1️⃣ التأكد من وجود عمود notes
ALTER TABLE transaction_logs 
ADD COLUMN IF NOT EXISTS notes text;

-- 2️⃣ تحديث Schema Cache
NOTIFY pgrst, 'reload schema';

SELECT '✅ Schema cache refreshed - notes column ensured' as status;
