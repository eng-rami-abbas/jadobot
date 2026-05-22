-- =====================================================
-- 🤖 إضافة حساب البوت الرئيسي (JADO BOT ADMIN)
-- =====================================================

-- إضافة المستخدم بالأعمدة الموجودة فقط
INSERT INTO users (telegram_id, username, balance_syp, created_at)
VALUES (
    7179419936,
    'jado_bot_admin',
    0,
    NOW()
)
ON CONFLICT (telegram_id) DO NOTHING;

SELECT 
    telegram_id,
    username,
    balance_syp
FROM users 
WHERE telegram_id = 7179419936;
