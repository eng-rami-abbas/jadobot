-- =====================================================
-- 🔥 إعداد جدول طرق السحب
-- =====================================================

-- حذف الجدول إذا كان موجوداً
DROP TABLE IF EXISTS withdrawal_methods CASCADE;

-- إنشاء جدول طرق السحب
CREATE TABLE withdrawal_methods (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,                    -- اسم طريقة السحب (Syriatel Cash, Bemo...)
  key text UNIQUE NOT NULL,              -- مفتاح فريد (syriatel_cash, bemo...)
  account_number text DEFAULT '',        -- رقم الحساب/المحفظة
  account_holder text DEFAULT '',        -- اسم صاحب الحساب
  title text DEFAULT '',                 -- العنوان المختصر
  emoji text DEFAULT '💳',               -- الإيموجي
  message_template text DEFAULT '',      -- قالب الرسالة للمستخدم
  fee_percentage decimal(5,2) DEFAULT 0, -- نسبة خصم السحب
  min_amount decimal(18,2) DEFAULT 25000,   -- الحد الأدنى
  max_amount decimal(18,2) DEFAULT 10000000, -- الحد الأقصى
  input_label text DEFAULT 'أدخل رقم الحساب', -- نص حقل الإدخال
  is_active boolean DEFAULT true,
  sort_order int DEFAULT 0,
  created_at timestamptz DEFAULT now()
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
-- 🔥 إضافة إعدادات نسبة الخصم العامة
-- =====================================================

-- حذف الإعدادات القديمة إذا كانت موجودة
DELETE FROM app_settings WHERE key = 'withdrawal_fee_percentage';

-- إضافة إعداد نسبة الخصم الافتراضية
INSERT INTO app_settings (key, value, description) VALUES 
  ('withdrawal_fee_percentage', '5.00', 'نسبة خصم السحب الافتراضية (%)');

-- =====================================================
-- 🔥 إضافة بعض طرق السحب الافتراضية
-- =====================================================

INSERT INTO withdrawal_methods (name, key, account_number, title, emoji, message_template, fee_percentage, min_amount, max_amount, input_label, sort_order) VALUES
  ('Syriatel Cash', 'syriatel_cash', '', 'سيريتل كاش', '📱', 'أرسل المبلغ إلى: 0991005298', 5.00, 25000, 10000000, 'أدخل رقم حساب سيريتل كاش', 1),
  ('Bemo Bank', 'bemo', '', 'بنك بيمو', '🏦', 'تحويل بنكي إلى حساب Bemo', 5.00, 10000, 5000000, 'أدخل رقم حساب Bemo', 2),
  ('Payeer', 'payeer', '', 'بايير', '💳', 'تحويل إلى محفظة Payeer', 3.00, 1000, 1000000, 'أدخل رقم حساب Payeer', 3),
  ('USDT TRC20', 'usdt_trc20', '', 'USDT TRC20', '💰', 'تحويل USDT عبر شبكة TRC20', 2.00, 10000, 5000000, 'أدخل عنوان محفظة USDT', 4),
  ('Sham Cash', 'sham_cash', '', 'شام كاش', '🇸🇾', 'تحويل عبر Sham Cash', 5.00, 25000, 10000000, 'أدخل رقم Sham Cash', 5);
