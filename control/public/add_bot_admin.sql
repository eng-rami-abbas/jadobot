-- =====================================================
-- 🤖 إضافة حساب البوت الرئيسي (JADO BOT ADMIN)
-- =====================================================

-- التحقق من وجود المستخدم أولاً
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE telegram_id = 7179419936) THEN
        INSERT INTO users (telegram_id, username, full_name, balance_syp, created_at)
        VALUES (
            7179419936,
            'jado_bot_admin',
            'JADO BOT ADMIN',
            0,
            NOW()
        );
        RAISE NOTICE '✅ JADO BOT ADMIN added successfully';
    ELSE
        RAISE NOTICE '⚠️ JADO BOT ADMIN already exists';
    END IF;
END $$;

SELECT 'Done' as status;
