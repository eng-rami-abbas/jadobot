-- =====================================================
-- 🔥 إعداد Realtime و Operation Number للسحوبات
-- =====================================================

-- إضافة جدول transactions إلى Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;

-- =====================================================
-- 🔥 إضافة عمود operation_number إذا مش موجود
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'operation_number'
    ) THEN
        ALTER TABLE transactions ADD COLUMN operation_number text;
    END IF;
END $$;

-- =====================================================
-- 🔥 إنشاء دالة لتوليد operation_number
-- =====================================================
CREATE OR REPLACE FUNCTION generate_operation_number()
RETURNS TRIGGER AS $$
DECLARE
    prefix text;
    year text;
    seq_num int;
    new_op_num text;
BEGIN
    -- تحديد البادئة حسب نوع العملية
    IF NEW.type = 'withdrawal' THEN
        prefix := 'W';
    ELSIF NEW.type = 'deposit' THEN
        prefix := 'D';
    ELSIF NEW.type = 'admin_withdraw' THEN
        prefix := 'AW';
    ELSIF NEW.type = 'admin_deposit' THEN
        prefix := 'AD';
    ELSE
        prefix := 'T';
    END IF;
    
    -- السنة الحالية (سنتين آخر رقمين)
    year := RIGHT(EXTRACT(YEAR FROM CURRENT_DATE)::text, 2);
    
    -- رقم تسلسلي بناءً على عدد العمليات لهذا النوع والسنة
    SELECT COUNT(*) + 1 INTO seq_num
    FROM transactions
    WHERE type = NEW.type
    AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_DATE);
    
    -- توليد الرقم النهائي
    new_op_num := prefix || year || LPAD(seq_num::text, 6, '0');
    
    NEW.operation_number := new_op_num;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 🔥 إنشاء Trigger لتوليد operation_number تلقائياً
-- =====================================================
DROP TRIGGER IF EXISTS set_operation_number ON transactions;

CREATE TRIGGER set_operation_number
    BEFORE INSERT ON transactions
    FOR EACH ROW
    WHEN (NEW.operation_number IS NULL)
    EXECUTE FUNCTION generate_operation_number();

-- =====================================================
-- 🔥 إضافة amount_syp إذا مش موجود
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'amount_syp'
    ) THEN
        ALTER TABLE transactions ADD COLUMN amount_syp decimal(15,2);
    END IF;
END $$;

-- =====================================================
-- 🔥 تحديث السجلات القديمة
-- =====================================================
-- تحويل amount من فلس إلى ليرة سورية (قسمة على 100)
UPDATE transactions 
SET amount_syp = amount / 100.0
WHERE amount_syp IS NULL AND amount IS NOT NULL;

-- توليد operation_number للسجلات القديمة اللي ما عندها
UPDATE transactions 
SET operation_number = 
    CASE type
        WHEN 'withdrawal' THEN 'W' || RIGHT(EXTRACT(YEAR FROM created_at)::text, 2) || LPAD(id::text, 6, '0')
        WHEN 'deposit' THEN 'D' || RIGHT(EXTRACT(YEAR FROM created_at)::text, 2) || LPAD(id::text, 6, '0')
        WHEN 'admin_withdraw' THEN 'AW' || RIGHT(EXTRACT(YEAR FROM created_at)::text, 2) || LPAD(id::text, 6, '0')
        WHEN 'admin_deposit' THEN 'AD' || RIGHT(EXTRACT(YEAR FROM created_at)::text, 2) || LPAD(id::text, 6, '0')
        ELSE 'T' || RIGHT(EXTRACT(YEAR FROM created_at)::text, 2) || LPAD(id::text, 6, '0')
    END
WHERE operation_number IS NULL;

-- =====================================================
-- 🔥 التأكد من وجود الأعمدة المطلوبة للسحب
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'account_number'
    ) THEN
        ALTER TABLE transactions ADD COLUMN account_number text;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'method'
    ) THEN
        ALTER TABLE transactions ADD COLUMN method text;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' AND column_name = 'fee_amount'
    ) THEN
        ALTER TABLE transactions ADD COLUMN fee_amount integer DEFAULT 0;
    END IF;
END $$;

-- =====================================================
-- ✅ تأكيد الإعدادات
-- =====================================================
SELECT 'Realtime enabled for transactions' as status;
SELECT 'operation_number trigger created' as status;
SELECT COUNT(*) as total_transactions FROM transactions;
SELECT COUNT(*) as pending_withdrawals FROM transactions WHERE type = 'withdrawal' AND status = 'pending';
