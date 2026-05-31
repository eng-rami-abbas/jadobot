-- =====================================================
-- 🔥 فحص جدول transaction_logs
-- =====================================================

-- 1️⃣ هيكل الجدول
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'transaction_logs'
ORDER BY ordinal_position;

-- 2️⃣ عدد السجلات
SELECT COUNT(*) as total_records FROM transaction_logs;

-- 3️⃣ آخر 5 سجلات
SELECT * FROM transaction_logs
ORDER BY created_at DESC
LIMIT 5;

-- 4️⃣ RLS Policy
SELECT policyname, permissive, cmd, qual
FROM pg_policies
WHERE tablename = 'transaction_logs';
