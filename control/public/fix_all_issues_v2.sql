-- =====================================================
-- 🔥 SQL شامل لإصلاح جميع المشاكل (مُحسّن)
-- =====================================================

-- 1️⃣ التأكد من وجود pending_notifications مع جميع الأعمدة
CREATE TABLE IF NOT EXISTS pending_notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    message text NOT NULL,
    status text DEFAULT 'pending',
    broadcast_id uuid,
    error_message text,
    created_at timestamptz DEFAULT now(),
    sent_at timestamptz
);

-- إضافة الأعمدة المفقودة (بشكل منفصل)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pending_notifications' AND column_name = 'broadcast_id') THEN
        ALTER TABLE pending_notifications ADD COLUMN broadcast_id uuid;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pending_notifications' AND column_name = 'error_message') THEN
        ALTER TABLE pending_notifications ADD COLUMN error_message text;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pending_notifications' AND column_name = 'sent_at') THEN
        ALTER TABLE pending_notifications ADD COLUMN sent_at timestamptz;
    END IF;
END $$;

-- 2️⃣ التأكد من وجود transaction_logs
CREATE TABLE IF NOT EXISTS transaction_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    username text,
    type text NOT NULL,
    amount_syp integer NOT NULL,
    status text DEFAULT 'pending',
    wallet_name text,
    operation_number integer,
    notes text,
    created_at timestamptz DEFAULT now()
);

-- 3️⃣ RLS - حذف وإعادة إنشاء
ALTER TABLE pending_notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pending_notif_all ON pending_notifications;
CREATE POLICY pending_notif_all ON pending_notifications FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE transaction_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tx_logs_all ON transaction_logs;
CREATE POLICY tx_logs_all ON transaction_logs FOR ALL USING (true) WITH CHECK (true);

-- 4️⃣ Realtime
DO $$ 
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE pending_notifications;
EXCEPTION WHEN others THEN
    NULL;
END $$;

DO $$ 
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE transaction_logs;
EXCEPTION WHEN others THEN
    NULL;
END $$;

-- 5️⃣ فهارس
CREATE INDEX IF NOT EXISTS idx_pending_notif_status ON pending_notifications(status);
CREATE INDEX IF NOT EXISTS idx_pending_notif_telegram ON pending_notifications(telegram_id);
CREATE INDEX IF NOT EXISTS idx_tx_logs_telegram ON transaction_logs(telegram_id);
CREATE INDEX IF NOT EXISTS idx_tx_logs_type ON transaction_logs(type);

-- 6️⃣ فحص البيانات
SELECT 
    'pending_notifications' as table_name, 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'sent') as sent,
    COUNT(*) FILTER (WHERE status = 'failed') as failed
FROM pending_notifications;

-- 7️⃣ تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ All tables fixed' as status;
