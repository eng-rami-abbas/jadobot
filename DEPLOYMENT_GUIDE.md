# 🚀 Jadoo Bot Deployment Guide - Railway

## 📋 المتطلبات الأساسية

1. حساب على Railway (https://railway.app)
2. حساب على Supabase (https://supabase.com)
3. حساب على GitHub
4. بوت تلغرام مع Token

## 🗂️ هيكلية المشروع بعد التحديث

```
jadoo-bot-latest/
├── bot_src/                    # البوت (Python)
│   ├── bot.py                  # الملف الرئيسي للبوت
│   ├── database/
│   │   └── supabase_client.py  # عميل Supabase الجديد
│   ├── config/
│   │   └── telegram.py         # الإعدادات (تقرأ من .env)
│   ├── .env.example           # قالب المتغيرات البيئية
│   ├── Dockerfile             # للنشر على Railway
│   ├── railway.json           # إعدادات Railway
│   └── requirements.txt       # الاعتماديات
├── control/                   # لوحة التحكم (React)
│   ├── src/
│   ├── Dockerfile            # للنشر على Railway
│   ├── railway.json          # إعدادات Railway
│   └── package.json          # الاعتماديات
└── DEPLOYMENT_GUIDE.md       # هذا الملف
```

## 🛠️ الخطوة 1: إعداد Supabase

1. **إنشاء مشروع جديد** في Supabase
2. **إنشاء الجداول المطلوبة**:

```sql
-- Users Table
CREATE TABLE users (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  telegram_id TEXT UNIQUE NOT NULL,
  username TEXT,
  first_name TEXT,
  balance_syp DECIMAL DEFAULT 0,
  balance_usd DECIMAL DEFAULT 0,
  is_blocked BOOLEAN DEFAULT FALSE,
  operations_count INTEGER DEFAULT 0,
  total_deposits DECIMAL DEFAULT 0,
  agreed_terms BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transactions Table
CREATE TABLE transactions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  telegram_id TEXT NOT NULL,
  type TEXT NOT NULL,
  method TEXT DEFAULT 'manual',
  amount DECIMAL NOT NULL,
  transfer_num TEXT DEFAULT '-',
  status TEXT DEFAULT 'pending',
  note TEXT DEFAULT '',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages Table
CREATE TABLE messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  telegram_id TEXT NOT NULL,
  username TEXT,
  content TEXT NOT NULL,
  direction TEXT DEFAULT 'incoming',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Settings Table
CREATE TABLE settings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Notifications Table
CREATE TABLE notifications (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  telegram_id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  type TEXT DEFAULT 'info',
  is_sent BOOLEAN DEFAULT FALSE,
  error TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  sent_at TIMESTAMP WITH TIME ZONE
);

-- Bot Logs Table
CREATE TABLE bot_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  type TEXT NOT NULL,
  message TEXT NOT NULL,
  telegram_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- App Settings Table
CREATE TABLE app_settings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

3. **الحصول على بيانات الاعتماد**:
   - Project URL
   - Service Role Key
   - Anonymous Key

## 📤 الخطوة 2: رفع الكود على GitHub

1. **إنشاء مستودع جديد** على GitHub
2. **رفع المشروع**:

```bash
git init
git add .
git commit -m "Initial commit - Ready for Railway deployment"
git branch -M main
git remote add origin https://github.com/yourusername/jadoo-bot.git
git push -u origin main
```

## 🚂 الخطوة 3: نشر البوت على Railway

### 3.1 إنشاء مشروع البوت

1. **تسجيل الدخول** إلى Railway
2. **New Project** → **Deploy from GitHub repo**
3. **اختيار مستودع** البوت
4. **إعدادات البيئة**:

```
# Telegram Configuration
BOT_TOKEN=your_telegram_bot_token_here
PARENT_ID=2730826
ADMIN_TELEGRAM_ID=7179419936
ADMIN_CHAT_ID=https://t.me/jadobotichancy

# Ichancy Platform Credentials
ICHANCY_USERNAME=jadobot@jado.nsp
ICHANCY_PASSWORD=Jado1993@@
COOKIE_STRING=your_cookie_string_here

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key_here

# Railway/Webhook Configuration
RAILWAY_ENVIRONMENT=production
WEBHOOK_URL=https://your-app-name.up.railway.app/webhook
PORT=8080

# Security
SECRET_KEY=your_secret_key_here_for_sessions
DEBUG=false
```

5. **نشر المشروع**

### 3.2 إعداد Webhook

1. **بعد النشر**، احصل على Railway URL
2. **إعداد Webhook** للبوت:

```bash
# استخدم curl أو أي API client
curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://your-app-name.up.railway.app/webhook",
       "drop_pending_updates": true
     }'
```

## 🖥️ الخطوة 4: نشر لوحة التحكم على Railway

### 4.1 إنشاء مشروع لوحة التحكم

1. **New Project** → **Deploy from GitHub repo**
2. **اختيار مستودع** لوحة التحكم
3. **إعدادات البيئة**:

```
# Supabase Configuration
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Node Environment
NODE_ENV=production
```

4. **نشر المشروع**

## 🔧 الخطوة 5: التحقق والاختبار

### 5.1 التحقق من البوت

1. **فحص الـ Health Check**:
   ```bash
   curl https://your-app-name.up.railway.app/health
   ```

2. **اختبار البوت**:
   - أرسل `/start` للبوت
   - تحقق من استجابة البوت

### 5.2 التحقق من لوحة التحكم

1. **زيارة لوحة التحكم**:
   ```
   https://your-control-app.up.railway.app
   ```

2. **تسجيل الدخول** باستخدام بيانات Supabase

## 📊 الخطوة 6: إعدادات الإنتاج

### 6.1 إعدادات Supabase

1. **تفعيل Realtime** للجداول:
   - transactions
   - messages
   - notifications

2. **إنشاء RLS Policies**:

```sql
-- Users table RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own data" ON users
  FOR SELECT USING (auth.uid()::text = telegram_id);

-- Transactions table RLS
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own transactions" ON transactions
  FOR SELECT USING (auth.uid()::text = telegram_id);
```

### 6.2 إعدادات Railway

1. **إضافة Custom Domain** (اختياري)
2. **إعداد Monitoring**
3. **إعداد Alerts**

## 🚨 استكشاف الأخطاء

### مشاكل شائعة:

1. **Webhook لا يعمل**:
   - تحقق من Railway URL
   - تأكد من أن PORT=8080
   - تحقق من إعدادات Telegram Bot API

2. **الاتصال بـ Supabase**:
   - تحقق من URL و Key
   - تأكد من أن الجداول موجودة
   - تحقق من RLS policies

3. **Build Errors**:
   - تحقق من requirements.txt
   - تأكد من إصدارات Python متوافقة

## 🔄 التحديثات المستقبلية

1. **إضافة CI/CD** مع GitHub Actions
2. **إضافة Monitoring** وAlerts
3. **تحسين الأداء** والتوسع
4. **إضافة Tests** تلقائية

## 📞 الدعم

- **Railway Documentation**: https://docs.railway.app
- **Supabase Documentation**: https://docs.supabase.com
- **python-telegram-bot**: https://docs.python-telegram-bot.org

---

**ملاحظة**: تأكد من أن جميع المتغيرات البيئية صحيحة قبل النشر النهائي.
