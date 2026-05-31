-- =====================================================
-- 🔥 إنشاء جدول الإشعارات المعلقة (pending_notifications)
-- =====================================================

CREATE TABLE IF NOT EXISTS pending_notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    message text NOT NULL,
    status text DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error_message text,
    created_at timestamptz DEFAULT now(),
    sent_at timestamptz
);

-- فهارس
CREATE INDEX IF NOT EXISTS idx_pending_notif_status ON pending_notifications(status);
CREATE INDEX IF NOT EXISTS idx_pending_notif_telegram ON pending_notifications(telegram_id);
CREATE INDEX IF NOT EXISTS idx_pending_notif_created ON pending_notifications(created_at);

-- RLS - مفتوح للجميع
ALTER TABLE pending_notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pending_notif_all ON pending_notifications;
CREATE POLICY pending_notif_all ON pending_notifications FOR ALL USING (true) WITH CHECK (true);

-- Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE pending_notifications;

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ pending_notifications table created' as status;
