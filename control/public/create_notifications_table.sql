-- =====================================================
-- 🔥 إنشاء جدول الإشعارات (إذا غير موجود)
-- =====================================================

-- إنشاء الجدول
CREATE TABLE IF NOT EXISTS notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type text NOT NULL CHECK (type IN ('deposit', 'withdrawal', 'message', 'events', 'user', 'gift-codes', 'system')),
    title text NOT NULL,
    body text NOT NULL,
    is_read boolean DEFAULT false,
    data jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now()
);

-- فهارس
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(is_read) WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);

-- RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS notifications_all ON notifications;
CREATE POLICY notifications_all ON notifications FOR ALL USING (true) WITH CHECK (true);

-- Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE notifications;

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ notifications table ready' as status;
