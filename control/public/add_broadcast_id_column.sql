-- =====================================================
-- 🔥 إضافة عمود broadcast_id للإشعارات
-- =====================================================

-- إضافة العمود إذا غير موجود
ALTER TABLE pending_notifications 
ADD COLUMN IF NOT EXISTS broadcast_id uuid REFERENCES broadcast_messages(id);

-- إضافة فهرس
CREATE INDEX IF NOT EXISTS idx_pending_notif_broadcast ON pending_notifications(broadcast_id);

-- تحديث Schema
NOTIFY pgrst, 'reload schema';

SELECT '✅ broadcast_id column added' as status;
