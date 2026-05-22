-- =====================================================
-- 🔥 إعداد جميع الميزات الجديدة
-- =====================================================

-- =====================================================
-- 1️⃣ نظام أكواد الهدايا (Gift Codes)
-- =====================================================

-- إنشاء جدول أكواد الهدايا
CREATE TABLE IF NOT EXISTS gift_codes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL,
    amount integer NOT NULL,
    is_used boolean DEFAULT false,
    used_by bigint,
    used_at timestamp with time zone,
    created_by bigint,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    notes text
);

-- تفعيل RLS
ALTER TABLE gift_codes ENABLE ROW LEVEL SECURITY;

-- إنشاء Policies
DROP POLICY IF EXISTS "auth_read_gift_codes" ON gift_codes;
DROP POLICY IF EXISTS "auth_insert_gift_codes" ON gift_codes;
DROP POLICY IF EXISTS "auth_update_gift_codes" ON gift_codes;
DROP POLICY IF EXISTS "auth_delete_gift_codes" ON gift_codes;

CREATE POLICY "auth_read_gift_codes" ON gift_codes FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_gift_codes" ON gift_codes FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_gift_codes" ON gift_codes FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "auth_delete_gift_codes" ON gift_codes FOR DELETE TO authenticated USING (true);

-- تفعيل Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE gift_codes;

-- =====================================================
-- 2️⃣ نسبة البونص للمحافظ (Bonus Percentage)
-- =====================================================

-- إضافة عمود البونص لجدول المحافظ
ALTER TABLE wallets 
ADD COLUMN IF NOT EXISTS bonus_percentage decimal(5,2) DEFAULT 0;

-- =====================================================
-- 3️⃣ تعديل جدول الإحالات لدعم ترسيت العداد
-- =====================================================

-- إضافة عمود last_reset للاحتفاظ بتاريخ آخر ترسيت
ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS last_reset timestamp with time zone DEFAULT timezone('utc'::text, now());

-- إضافة عمود total_referrals لحفظ العدد التراكمي
ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS total_referrals integer DEFAULT 0;

-- =====================================================
-- 4️⃣ إعدادات البوت (Bot Settings)
-- =====================================================

-- إضافة إعدادات جديدة لجدول app_settings
INSERT INTO app_settings (key, value, description) VALUES
    ('bot_telegram_id', '', 'ID التلغرام الرئيسي للبوت'),
    ('bot_enabled', 'true', 'حالة تشغيل البوت (true/false)'),
    ('bot_stop_message', '⏸️ البوت متوقف مؤقتاً. يرجى المحاولة لاحقاً.', 'رسالة ظهور عند إيقاف البوت'),
    ('gift_code_success_message', '🎉 تهانينا! تم استخدام كود الهدية بنجاح!\n\n💰 تم إضافة {amount} ل.س لرصيدك.', 'رسالة نجاح استخدام كود الهدية'),
    ('gift_code_used_message', '⚠️ هذا الكود مستخدم مسبقاً.', 'رسالة خطأ: الكود مستخدم'),
    ('gift_code_invalid_message', '❌ الكود غير صحيح.', 'رسالة خطأ: كود غير موجود'),
    ('broadcast_message_template', '📢 رسالة من الإدارة:\n\n{message}', 'قالب الرسائل الجماعية'),
    ('referral_reset_cron', '0 20 */10 * *', 'Cron job لترسيت الإحالات كل 10 أيام الساعة 8 مساءً')
ON CONFLICT (key) DO NOTHING;

-- =====================================================
-- 5️⃣ جدول الرسائل الجماعية (Broadcast Messages)
-- =====================================================

CREATE TABLE IF NOT EXISTS broadcast_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message text NOT NULL,
    sent_by bigint,
    sent_count integer DEFAULT 0,
    failed_count integer DEFAULT 0,
    status text DEFAULT 'pending',
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    completed_at timestamp with time zone
);

ALTER TABLE broadcast_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth_read_broadcast" ON broadcast_messages;
DROP POLICY IF EXISTS "auth_insert_broadcast" ON broadcast_messages;

CREATE POLICY "auth_read_broadcast" ON broadcast_messages FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_broadcast" ON broadcast_messages FOR INSERT TO authenticated WITH CHECK (true);

ALTER PUBLICATION supabase_realtime ADD TABLE broadcast_messages;

-- =====================================================
-- 6️⃣ دالة ترسيت الإحالات
-- =====================================================

CREATE OR REPLACE FUNCTION reset_referral_counters()
RETURNS void AS $$
BEGIN
    -- حفظ العدد التراكمي قبل الترسيت
    UPDATE referrals 
    SET total_referrals = total_referrals + referral_count,
        referral_count = 0,
        last_reset = timezone('utc'::text, now());
    
    -- تسجيل الحدث
    INSERT INTO events (event_type, details)
    VALUES ('referral_reset', jsonb_build_object(
        'reset_time', timezone('utc'::text, now()),
        'affected_users', (SELECT COUNT(*) FROM referrals)
    ));
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- ✅ التحقق من الإنشاء
-- =====================================================

SELECT 'gift_codes table created' as status WHERE EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_name = 'gift_codes'
);

SELECT 'bonus_percentage column added' as status WHERE EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'wallets' AND column_name = 'bonus_percentage'
);

SELECT 'referral columns updated' as status WHERE EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'referrals' AND column_name = 'total_referrals'
);
