-- =====================================================
-- 🔥 SQL شامل لجميع الإصلاحات
-- =====================================================

-- 1️⃣ إصلاح RLS للمحافظ
DROP POLICY IF EXISTS wallets_all ON wallets;
DROP POLICY IF EXISTS wallets_select ON wallets;
DROP POLICY IF EXISTS wallets_insert ON wallets;
DROP POLICY IF EXISTS wallets_update ON wallets;
DROP POLICY IF EXISTS wallets_delete ON wallets;

CREATE POLICY wallets_select ON wallets FOR SELECT USING (true);
CREATE POLICY wallets_insert ON wallets FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY wallets_update ON wallets FOR UPDATE USING (auth.role() = 'authenticated') WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY wallets_delete ON wallets FOR DELETE USING (auth.role() = 'authenticated');

ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER PUBLICATION supabase_realtime ADD TABLE wallets;

-- 2️⃣ إضافة أعمدة إعدادات السحب
ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS value text;

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ جميع الإصلاحات تم تطبيقها' as status;
