-- =====================================================
-- 🔥 فحص الجداول والبيانات
-- =====================================================

-- 1️⃣ فحص pending_notifications
SELECT 'pending_notifications' as table_name, COUNT(*) as count FROM pending_notifications;

-- 2️⃣ فحص transaction_logs
SELECT 'transaction_logs' as table_name, COUNT(*) as count FROM transaction_logs;

-- 3️⃣ فحص broadcast_messages
SELECT 'broadcast_messages' as table_name, COUNT(*) as count FROM broadcast_messages;

-- 4️⃣ آخر 5 إشعارات معلقة
SELECT id, telegram_id, status, LEFT(message, 50) as message_preview, created_at
FROM pending_notifications
ORDER BY created_at DESC
LIMIT 5;

-- 5️⃣ هيكل pending_notifications
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pending_notifications';
