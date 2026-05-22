-- =====================================================
-- 🔧 التحقق من إعدادات Realtime (بدون أخطاء)
-- =====================================================

-- التحقق فقط - لا خطأ إذا موجود
DO $$
BEGIN
    -- التأكد من وجود الجدول
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'notifications') THEN
        CREATE TABLE notifications (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            type text NOT NULL,
            title text NOT NULL,
            body text NOT NULL,
            is_read boolean DEFAULT false,
            data jsonb DEFAULT '{}',
            created_at timestamptz DEFAULT now()
        );
    END IF;
END $$;

-- فهارس (بدون خطأ إذا موجودة)
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(is_read) WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- سياسة (حذف وإعادة إنشاء)
DROP POLICY IF EXISTS notifications_all ON notifications;
CREATE POLICY notifications_all ON notifications FOR ALL USING (true) WITH CHECK (true);

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ notifications ready' as status;
