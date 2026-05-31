-- ============================================
-- إصلاح Row Level Security للمحافظ
-- ============================================

-- الخيار 1: السماح بالقراءة العامة (للتطوير فقط)
-- هذا يسمح لأي شخص بقراءة المحافظ بدون تسجيل دخول
CREATE POLICY IF NOT EXISTS "public_read_wallets" 
  ON wallets 
  FOR SELECT 
  USING (true);

-- أو الخيار 2: السماح بالقراءة للمستخدمين المصادقين + Anonymous
DROP POLICY IF EXISTS "auth_read_wallets" ON wallets;
CREATE POLICY "allow_all_read_wallets" 
  ON wallets 
  FOR SELECT 
  USING (true);

-- إعادة إنشاء السياسات الأخرى للكتابة (تتطلب تسجيل دخول)
DROP POLICY IF EXISTS "auth_insert_wallets" ON wallets;
DROP POLICY IF EXISTS "auth_update_wallets" ON wallets;
DROP POLICY IF EXISTS "auth_delete_wallets" ON wallets;

CREATE POLICY "auth_insert_wallets" 
  ON wallets 
  FOR INSERT 
  TO authenticated 
  WITH CHECK (true);

CREATE POLICY "auth_update_wallets" 
  ON wallets 
  FOR UPDATE 
  TO authenticated 
  USING (true) 
  WITH CHECK (true);

CREATE POLICY "auth_delete_wallets" 
  ON wallets 
  FOR DELETE 
  TO authenticated 
  USING (true);

-- ============================================
-- التحقق من السياسات
-- ============================================
SELECT 
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
FROM pg_policies 
WHERE tablename = 'wallets';
