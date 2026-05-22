-- جدول المستخدمين لعجلة الروليت
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    balance INTEGER DEFAULT 0,
    pending_bonus INTEGER DEFAULT 0,
    last_deposit_date DATE,
    last_deposit_amount INTEGER DEFAULT 0,
    last_deposit_currency TEXT DEFAULT 'SYP',
    last_spin_date DATE,
    total_spins INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- فهرس للبحث السريع
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);

-- سياسة Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- السماح للجميع بالقراءة والكتابة (للبوت)
CREATE POLICY "Allow all operations" ON users
    FOR ALL USING (true) WITH CHECK (true);
