-- =====================================================
-- 🔥 إعداد جدول طرق السحب (مبسط)
-- =====================================================

-- حذف الجدول إذا كان موجوداً
DROP TABLE IF EXISTS withdrawal_methods CASCADE;

-- إنشاء جدول طرق السحب المبسط
CREATE TABLE withdrawal_methods (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,                    -- اسم طريقة السحب
  key text UNIQUE NOT NULL,              -- مفتاح فريد
  emoji text DEFAULT '💳',               -- الإيموجي
  fee_percentage decimal(5,2) DEFAULT 0, -- نسبة خصم السحب (ضرورية)
  input_label text DEFAULT 'أدخل رقم الحساب', -- نص طلب العنوان
  is_active boolean DEFAULT true,
  sort_order int DEFAULT 0
);

-- إعداد الصلاحيات
ALTER TABLE withdrawal_methods ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_withdrawal_methods" ON withdrawal_methods FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_withdrawal_methods" ON withdrawal_methods FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_withdrawal_methods" ON withdrawal_methods FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "auth_delete_withdrawal_methods" ON withdrawal_methods FOR DELETE TO authenticated USING (true);

-- إضافة للـ Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE withdrawal_methods;

-- =====================================================
-- 🔥 إضافة رسائل السحب القابلة للتخصيص
-- =====================================================

DELETE FROM app_settings WHERE key IN ('withdrawal_fee_percentage', 'withdrawal_approved_message', 'withdrawal_rejected_message');

INSERT INTO app_settings (key, value, description) VALUES 
  ('withdrawal_fee_percentage', '5.00', 'نسبة خصم السحب الافتراضية (%)'),
  ('withdrawal_approved_message', '✅ تمت الموافقة على طلب سحبك!\n\n💰 المبلغ: {amount_syp} ل.س\n💸 نسبة الخصم: {fee_percentage}%\n✅ المبلغ الصافي: {net_amount} ل.س\n🏦 طريقة السحب: {method_name}\n📋 رقم العملية: {operation_number}', 'رسالة موافقة السحب'),
  ('withdrawal_rejected_message', '❌ تم رفض طلب سحبك\n\n💰 المبلغ: {amount_syp} ل.س\n🏦 طريقة السحب: {method_name}\n📋 رقم العملية: {operation_number}\n\nيرجى التواصل مع الدعم.', 'رسالة رفض السحب');

-- =====================================================
-- 🔥 إضافة طرق سحب افتراضية
-- =====================================================

INSERT INTO withdrawal_methods (name, key, emoji, fee_percentage, input_label, sort_order) VALUES
  ('Syriatel Cash', 'syriatel_cash', '📱', 5.00, 'أدخل رقم حساب سيريتل كاش', 1),
  ('Bemo Bank', 'bemo', '🏦', 5.00, 'أدخل رقم حساب Bemo', 2),
  ('Payeer', 'payeer', '💳', 3.00, 'أدخل رقم حساب Payeer', 3),
  ('USDT TRC20', 'usdt_trc20', '💰', 2.00, 'أدخل عنوان محفظة USDT', 4);
