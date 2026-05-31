-- =====================================================
-- 🔥 إنشاء جدول broadcast_messages
-- =====================================================

CREATE TABLE IF NOT EXISTS broadcast_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message text NOT NULL,
    sent_count integer DEFAULT 0,
    failed_count integer DEFAULT 0,
    status text DEFAULT 'pending',
    created_at timestamptz DEFAULT now(),
    completed_at timestamptz
);

-- فهارس
CREATE INDEX IF NOT EXISTS idx_broadcast_status ON broadcast_messages(status);
CREATE INDEX IF NOT EXISTS idx_broadcast_created ON broadcast_messages(created_at);

-- RLS
ALTER TABLE broadcast_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS broadcast_all ON broadcast_messages;
CREATE POLICY broadcast_all ON broadcast_messages FOR ALL USING (true) WITH CHECK (true);

-- Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE broadcast_messages;

-- Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ broadcast_messages table created' as result;
