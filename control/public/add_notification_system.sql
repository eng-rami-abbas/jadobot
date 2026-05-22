-- ============================================
-- نظام إشعارات تلغرام - Telegram Notification System
-- ============================================

-- 1. جدول الإشعارات المعلقة (Pending Notifications)
-- يتم إضافة الإشعار هنا من لوحة التحكم ويقرأه البوت
CREATE TABLE IF NOT EXISTS pending_notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id bigint NOT NULL,
  message text NOT NULL,
  status text DEFAULT 'pending' CHECK (status IN ('pending','sent','failed')),
  created_at timestamptz DEFAULT now(),
  sent_at timestamptz,
  error_message text
);
ALTER TABLE pending_notifications ENABLE ROW LEVEL SECURITY;

-- السياسات
CREATE POLICY IF NOT EXISTS "public_read_notifications" 
  ON pending_notifications FOR SELECT USING (true);
  
CREATE POLICY IF NOT EXISTS "auth_insert_notifications" 
  ON pending_notifications FOR INSERT TO authenticated WITH CHECK (true);
  
CREATE POLICY IF NOT EXISTS "auth_update_notifications" 
  ON pending_notifications FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- 2. إعدادات رسائل الإشعارات القابلة للتخصيص
-- إضافة الإعدادات لرسائل الموافقة والرفض
INSERT INTO app_settings (key, value) VALUES
  ('deposit_approved_message', 
   '✅ تمت الموافقة على إيداعك!

💰 المبلغ: {amount_syp} ل.س
🏦 المحفظة: {wallet_name}
📊 رقم العملية: {operation_number}

تم إضافة المبلغ إلى رصيدك.'),
   
  ('deposit_rejected_message', 
   '❌ تم رفض إيداعك

💰 المبلغ: {amount_syp} ل.س
🏦 المحفظة: {wallet_name}
📊 رقم العملية: {operation_number}

يرجى التواصل مع الدعم للمزيد من المعلومات.')
  
ON CONFLICT (key) DO NOTHING;

-- 3. Realtime للإشعارات
ALTER PUBLICATION supabase_realtime ADD TABLE pending_notifications;

-- ============================================
-- التحقق من الإعدادات
-- ============================================
SELECT key, value FROM app_settings WHERE key LIKE '%deposit%';
