-- =====================================================
-- 🔥 إنشاء جدول سجل العمليات للبوت (transaction_logs)
-- =====================================================

CREATE TABLE IF NOT EXISTS transaction_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    username text,
    type text NOT NULL CHECK (type IN ('deposit', 'withdrawal', 'gift', 'admin_withdraw')),
    amount_syp integer NOT NULL,
    status text DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'rejected')),
    wallet_name text,
    operation_number integer,
    notes text,
    created_at timestamptz DEFAULT now()
);

-- فهارس
CREATE INDEX IF NOT EXISTS idx_tx_logs_telegram ON transaction_logs(telegram_id);
CREATE INDEX IF NOT EXISTS idx_tx_logs_type ON transaction_logs(type);
CREATE INDEX IF NOT EXISTS idx_tx_logs_status ON transaction_logs(status);
CREATE INDEX IF NOT EXISTS idx_tx_logs_created ON transaction_logs(created_at DESC);

-- RLS
ALTER TABLE transaction_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tx_logs_all ON transaction_logs;
CREATE POLICY tx_logs_all ON transaction_logs FOR ALL USING (true) WITH CHECK (true);

-- Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE transaction_logs;

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ transaction_logs table created' as status;
