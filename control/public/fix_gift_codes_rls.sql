-- =====================================================
-- 🔧 إصلاح RLS policy لجدول أكواد الهدايا
-- =====================================================

-- التأكد من وجود RLS مفعل
ALTER TABLE gift_codes ENABLE ROW LEVEL SECURITY;

-- حذف السياسات القديمة إذا وجدت
DROP POLICY IF EXISTS "Gift codes delete policy" ON gift_codes;
DROP POLICY IF EXISTS "Gift codes delete all" ON gift_codes;

-- إنشاء سياسة جديدة للحذف
CREATE POLICY "Gift codes delete all" ON gift_codes
    FOR DELETE
    TO public
    USING (true);

-- تحديث Schema Cache
NOTIFY pgrst, 'reload schema';

SELECT '✅ Fixed RLS delete policy for gift_codes' as status;
