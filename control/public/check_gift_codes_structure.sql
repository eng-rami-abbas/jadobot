-- =====================================================
-- 🔍 فحص بناء جدول gift_codes
-- =====================================================

-- عرض أعمدة الجدول
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'gift_codes'
ORDER BY ordinal_position;

-- عرض المفتاح الأساسي
SELECT kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'gift_codes' 
AND tc.constraint_type = 'PRIMARY KEY';

-- عرض بيانات من الجدول
SELECT * FROM gift_codes LIMIT 3;
