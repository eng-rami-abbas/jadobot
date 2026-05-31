-- =====================================================
-- 📝 إنشاء جدول events لتسجيل الأحداث
-- =====================================================

-- إنشاء الجدول
CREATE TABLE IF NOT EXISTS events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type text NOT NULL,
    telegram_id bigint NOT NULL,
    username text,
    details jsonb,
    created_at timestamptz DEFAULT now()
);

-- فهرس للبحث السريع
CREATE INDEX IF NOT EXISTS idx_events_telegram_id ON events(telegram_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);

-- تفعيل RLS
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- سياسة وصول
DROP POLICY IF EXISTS "Events full access" ON events;
CREATE POLICY "Events full access" ON events FOR ALL USING (true);

-- تحديث Schema Cache
NOTIFY pgrst, 'reload schema';

SELECT '✅ Events table created successfully' as status;
