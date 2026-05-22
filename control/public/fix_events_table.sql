-- =====================================================
-- 🔧 إصلاح جدول events
-- =====================================================

-- حذف الجدول القديم إذا موجود (مع التعامل مع dependencies)
DROP TABLE IF EXISTS events CASCADE;

-- إنشاء الجدول من جديد
CREATE TABLE events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type text NOT NULL,
    telegram_id bigint NOT NULL,
    username text,
    details jsonb,
    created_at timestamptz DEFAULT now()
);

-- فهرس للبحث السريع
CREATE INDEX idx_events_telegram_id ON events(telegram_id);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_created_at ON events(created_at DESC);

-- تفعيل RLS
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- سياسة وصول
CREATE POLICY "Events full access" ON events FOR ALL USING (true);

-- تحديث Schema Cache
NOTIFY pgrst, 'reload schema';

SELECT '✅ Events table fixed successfully' as status;
