-- جدول المستخدمين
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT UNIQUE NOT NULL,
  username TEXT,
  first_name TEXT,
  balance INTEGER DEFAULT 0,
  free_spins_remaining INTEGER DEFAULT 0,
  bonus_active BOOLEAN DEFAULT false,
  bonus_percentage INTEGER DEFAULT 5,
  last_spin_date DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- جدول الإيداعات
CREATE TABLE deposits (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id),
  amount INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- جدول التدويرات
CREATE TABLE spins (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id),
  result_type TEXT NOT NULL, -- money, bonus, free_spin, premium, lose
  result_value INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- جدول جوائز Telegram Premium المعلقة
CREATE TABLE premium_rewards (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id),
  processed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- جدول الجوائز الإضافية (اختياري)
CREATE TABLE bonus_rewards (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id),
  applied BOOLEAN DEFAULT false,
  percentage INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);