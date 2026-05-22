-- =====================================================
-- 🔥 إصلاح أعمدة جدول transactions المفقودة
-- =====================================================

-- إضافة الأعمدة المفقودة
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS account_number text,
ADD COLUMN IF NOT EXISTS method text,
ADD COLUMN IF NOT EXISTS fee_amount integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS operation_number text,
ADD COLUMN IF NOT EXISTS amount_syp decimal(15,2);

-- تحديث السجلات القديمة (amount → amount_syp)
UPDATE transactions 
SET amount_syp = amount / 100.0
WHERE amount_syp IS NULL AND amount IS NOT NULL;

-- إنشاء دالة توليد operation_number
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

-- ✅ تفعيل Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;

-- التأكد
SELECT 'Columns added successfully' as status;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'transactions' 
ORDER BY ordinal_position;
