-- =====================================================
-- 🔥 إصلاح RLS للمحافظ - السماح للـ Admin بالتعديل
-- =====================================================

-- تأكد من وجود الجدول
CREATE TABLE IF NOT EXISTS wallets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    key text UNIQUE NOT NULL,
    wallet_number text NOT NULL,
    address text,
    title text,
    image_url text,
    emoji text DEFAULT '💳',
    message_template text,
    is_active boolean DEFAULT true,
    sort_order integer DEFAULT 0,
    bonus_percentage decimal(5,2) DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- حذف السياسات القديمة إن وجدت
DROP POLICY IF EXISTS wallets_all ON wallets;
DROP POLICY IF EXISTS wallets_select ON wallets;
DROP POLICY IF EXISTS wallets_insert ON wallets;
DROP POLICY IF EXISTS wallets_update ON wallets;
DROP POLICY IF EXISTS wallets_delete ON wallets;

-- إنشاء سياسات جديدة
-- السماح للجميع بالقراءة (للبوت)
CREATE POLICY wallets_select ON wallets
    FOR SELECT USING (true);

-- السماح فقط للمستخدمين المسجلين دخولاً بالكتابة
CREATE POLICY wallets_insert ON wallets
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY wallets_update ON wallets
    FOR UPDATE USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY wallets_delete ON wallets
    FOR DELETE USING (auth.role() = 'authenticated');

-- تفعيل RLS
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;

-- تفعيل Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE wallets;

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ wallets RLS fixed - authenticated users can now edit' as status;
