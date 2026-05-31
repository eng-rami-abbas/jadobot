-- =====================================================
-- 🔥 إصلاح شامل لجدول transactions
-- =====================================================

-- أولاً: ننشئ الجدول من جديد إذا كان مفقوداً
CREATE TABLE IF NOT EXISTS transactions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id bigint NOT NULL,
    username text,
    type text NOT NULL,
    amount integer DEFAULT 0,
    amount_syp decimal(15,2),
    status text DEFAULT 'pending',
    account_number text,
    method text,
    fee_amount integer DEFAULT 0,
    operation_number text,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now())
);

-- إضافة الأعمدة المفقودة (IF NOT EXISTS)
DO $$
BEGIN
    -- amount
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'amount'
    ) THEN
        ALTER TABLE transactions ADD COLUMN amount integer DEFAULT 0;
    END IF;
    
    -- amount_syp
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'amount_syp'
    ) THEN
        ALTER TABLE transactions ADD COLUMN amount_syp decimal(15,2);
    END IF;
    
    -- account_number
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'account_number'
    ) THEN
        ALTER TABLE transactions ADD COLUMN account_number text;
    END IF;
    
    -- method
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'method'
    ) THEN
        ALTER TABLE transactions ADD COLUMN method text;
    END IF;
    
    -- fee_amount
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'fee_amount'
    ) THEN
        ALTER TABLE transactions ADD COLUMN fee_amount integer DEFAULT 0;
    END IF;
    
    -- operation_number
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'operation_number'
    ) THEN
        ALTER TABLE transactions ADD COLUMN operation_number text;
    END IF;
    
    -- status
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'status'
    ) THEN
        ALTER TABLE transactions ADD COLUMN status text DEFAULT 'pending';
    END IF;
    
    -- telegram_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'telegram_id'
    ) THEN
        ALTER TABLE transactions ADD COLUMN telegram_id bigint NOT NULL DEFAULT 0;
    END IF;
    
    -- username
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'username'
    ) THEN
        ALTER TABLE transactions ADD COLUMN username text;
    END IF;
    
    -- type
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'type'
    ) THEN
        ALTER TABLE transactions ADD COLUMN type text NOT NULL DEFAULT 'withdrawal';
    END IF;
END $$;

-- =====================================================
-- 🔥 تفعيل RLS وإنشاء Policies
-- =====================================================
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth_read_transactions" ON transactions;
DROP POLICY IF EXISTS "auth_insert_transactions" ON transactions;
DROP POLICY IF EXISTS "auth_update_transactions" ON transactions;

CREATE POLICY "auth_read_transactions" ON transactions FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_transactions" ON transactions FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_transactions" ON transactions FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- =====================================================
-- 🔥 تفعيل Realtime
-- =====================================================
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;

-- =====================================================
-- 🔥 إنشاء دالة توليد operation_number
-- =====================================================
CREATE OR REPLACE FUNCTION generate_operation_number()
RETURNS TRIGGER AS $$
DECLARE
    prefix text;
    year text;
    seq_num int;
BEGIN
    prefix := CASE NEW.type
        WHEN 'withdrawal' THEN 'W'
        WHEN 'deposit' THEN 'D'
        WHEN 'admin_withdraw' THEN 'AW'
        WHEN 'admin_deposit' THEN 'AD'
        ELSE 'T'
    END;
    year := RIGHT(EXTRACT(YEAR FROM CURRENT_DATE)::text, 2);
    
    SELECT COUNT(*) + 1 INTO seq_num
    FROM transactions 
    WHERE type = NEW.type 
    AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_DATE);
    
    NEW.operation_number := prefix || year || LPAD(seq_num::text, 6, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- إنشاء Trigger
DROP TRIGGER IF EXISTS set_operation_number ON transactions;
CREATE TRIGGER set_operation_number
    BEFORE INSERT ON transactions
    FOR EACH ROW 
    WHEN (NEW.operation_number IS NULL)
    EXECUTE FUNCTION generate_operation_number();

-- =====================================================
-- ✅ التحقق من الأعمدة
-- =====================================================
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'transactions' 
ORDER BY ordinal_position;
