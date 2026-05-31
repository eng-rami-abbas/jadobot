-- =====================================================
-- 🔥 إصلاح جميع الأعمدة المفقودة في كل الجداول
-- =====================================================

-- 1️⃣ جدول gift_codes
ALTER TABLE gift_codes 
ADD COLUMN IF NOT EXISTS is_used boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS used_by bigint REFERENCES users(telegram_id),
ADD COLUMN IF NOT EXISTS used_at timestamptz,
ADD COLUMN IF NOT EXISTS notes text;

-- 2️⃣ جدول wallets (نسبة البونص)
ALTER TABLE wallets 
ADD COLUMN IF NOT EXISTS bonus_percentage decimal(5,2) DEFAULT 0;

-- 3️⃣ جدول transactions (أعمدة البونص)
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS bonus_amount integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS bonus_percentage decimal(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_amount decimal(15,2);

-- 4️⃣ جدول users (الإحالات)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS referral_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_referrals integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS referral_code text UNIQUE;

-- 5️⃣ جدول broadcast_messages
ALTER TABLE broadcast_messages 
ADD COLUMN IF NOT EXISTS sent_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS failed_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS status text DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS completed_at timestamptz;

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

-- التحقق من جميع الأعمدة
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name IN ('gift_codes', 'wallets', 'transactions', 'users', 'broadcast_messages')
ORDER BY table_name, ordinal_position;
