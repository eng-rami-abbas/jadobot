-- =====================================================
-- 🤖 إضافة حساب البوت الرئيسي (JADO BOT ADMIN)
-- =====================================================

-- إضافة المستخدم (سيخفق إذا موجود بالفعل بسبب on_conflict)
INSERT INTO users (telegram_id, username, full_name, balance_syp, created_at)
VALUES (
    7179419936,
    'jado_bot_admin',
    'JADO BOT ADMIN',
    0,
    NOW()
)
ON CONFLICT (telegram_id) DO NOTHING;

SELECT 
    telegram_id,
    username,
    full_name,
    balance_syp
FROM users 
WHERE telegram_id = 7179419936;
