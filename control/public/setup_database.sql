-- ============================================================
-- Bot Admin Dashboard - Database Setup
-- Run this SQL in your Supabase SQL Editor
-- ============================================================

-- 1. Bot Users Table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id bigint UNIQUE NOT NULL,
  username text DEFAULT '',
  first_name text DEFAULT '',
  last_name text DEFAULT '',
  balance_syp decimal(18,2) DEFAULT 0,
  balance_usd decimal(18,4) DEFAULT 0,
  is_blocked boolean DEFAULT false,
  total_deposits decimal(18,2) DEFAULT 0,
  total_withdrawals decimal(18,2) DEFAULT 0,
  operations_count int DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  last_active timestamptz DEFAULT now()
);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_users" ON users FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_users" ON users FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_users" ON users FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- 2. Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  operation_number bigserial,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  telegram_id bigint,
  username text DEFAULT '',
  type text NOT NULL CHECK (type IN ('deposit','withdrawal','gift','admin_withdraw')),
  amount_usd decimal(18,4) DEFAULT 0,
  amount_syp decimal(18,2) DEFAULT 0,
  exchange_rate decimal(18,2) DEFAULT 0,
  status text DEFAULT 'completed' CHECK (status IN ('pending','completed','rejected')),
  wallet_name text DEFAULT '',
  wallet_address text DEFAULT '',
  notes text DEFAULT '',
  created_at timestamptz DEFAULT now()
);
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_transactions" ON transactions FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_transactions" ON transactions FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_transactions" ON transactions FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- 3. Messages Table
CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  telegram_id bigint,
  username text DEFAULT '',
  direction text NOT NULL CHECK (direction IN ('incoming','outgoing')),
  content text NOT NULL,
  is_read boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_messages" ON messages FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_messages" ON messages FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_messages" ON messages FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- 4. Wallets Table
CREATE TABLE IF NOT EXISTS wallets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  key text UNIQUE NOT NULL,
  wallet_number text NOT NULL,
  address text NOT NULL,
  title text DEFAULT '',
  image_url text DEFAULT '',
  emoji text DEFAULT '💳',
  is_active boolean DEFAULT true,
  message_template text DEFAULT 'يرجى الإيداع على المحفظة التالية',
  sort_order int DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_wallets" ON wallets FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_wallets" ON wallets FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_wallets" ON wallets FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "auth_delete_wallets" ON wallets FOR DELETE TO authenticated USING (true);

-- 5. App Settings Table
CREATE TABLE IF NOT EXISTS app_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key text UNIQUE NOT NULL,
  value text NOT NULL,
  updated_at timestamptz DEFAULT now()
);
ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_app_settings" ON app_settings FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_app_settings" ON app_settings FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_app_settings" ON app_settings FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- 6. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  type text NOT NULL,
  title text NOT NULL,
  body text NOT NULL,
  is_read boolean DEFAULT false,
  data jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_notifications" ON notifications FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_notifications" ON notifications FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_notifications" ON notifications FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- 7. Bot Balance Table
CREATE TABLE IF NOT EXISTS bot_balance (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  balance_syp decimal(18,2) DEFAULT 0,
  balance_usd decimal(18,4) DEFAULT 0,
  updated_at timestamptz DEFAULT now()
);
ALTER TABLE bot_balance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_bot_balance" ON bot_balance FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth_insert_bot_balance" ON bot_balance FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "auth_update_bot_balance" ON bot_balance FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- Default Settings
INSERT INTO app_settings (key, value) VALUES
  ('exchange_rate', '14500'),
  ('language', 'ar'),
  ('theme', 'dark'),
  ('bot_name', 'Bot Dashboard'),
  ('deposit_message', 'يرجى إرسال إيصال الدفع بعد إتمام عملية الإيداع'),
  ('min_deposit', '5'),
  ('min_withdrawal', '5')
ON CONFLICT (key) DO NOTHING;

-- Initial Balance
INSERT INTO bot_balance (balance_syp, balance_usd)
SELECT 0, 0 WHERE NOT EXISTS (SELECT 1 FROM bot_balance);

-- Sample Wallets
INSERT INTO wallets (name, key, wallet_number, address, title, message_template, sort_order) VALUES
  ('سيريتل كاش', 'syriatel_cash', '0991234567', '0991234567', 'سيريتل كاش', 'يرجى الإيداع على رقم سيريتل كاش التالي:', 1),
  ('MTN كاش', 'mtn_cash', '0951234567', '0951234567', 'MTN كاش', 'يرجى الإيداع على رقم MTN كاش التالي:', 2)
ON CONFLICT DO NOTHING;

-- Enable Realtime on all tables
ALTER PUBLICATION supabase_realtime ADD TABLE users;
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE notifications;
ALTER PUBLICATION supabase_realtime ADD TABLE bot_balance;
ALTER PUBLICATION supabase_realtime ADD TABLE wallets;
ALTER PUBLICATION supabase_realtime ADD TABLE app_settings;
ALTER TABLE users
ADD COLUMN role TEXT DEFAULT 'user';
-- ============================================================
-- After running this SQL:
-- 1. Go to Supabase Auth > Users and create an admin user
-- 2. Use that email/password to login to the dashboard
-- ============================================================
