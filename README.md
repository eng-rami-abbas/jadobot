# 🤖 Jadoo Bot - Railway Ready

## 📋 نظرة عامة

مشروع بوت تلغرام متكامل مع لوحة تحكم إدارية، تم تجهيزه بالكامل للنشر على Railway باستخدام Webhook و Supabase.

## 🏗️ الهيكلية

- **البوت**: Python 3.11 مع python-telegram-bot
- **لوحة التحكم**: React 18 + TypeScript + TailwindCSS
- **قاعدة البيانات**: Supabase (PostgreSQL)
- **النشر**: Docker + Railway

## ✅ التحديثات الرئيسية

### 🔧 التغييرات التقنية:
- ✅ تحويل من Polling إلى Webhook
- ✅ إزالة SQLite والاعتماد على Supabase فقط
- ✅ تأمين البيانات الحساسة مع متغيرات البيئة
- ✅ إضافة Docker configurations
- ✅ تحديث الاعتماديات للإنتاج

### 🚀 جاهزية النشر:
- ✅ Dockerfile للبوت ولوحة التحكم
- ✅ railway.json configurations
- ✅ .gitignore متكامل
- ✅ دليل نشر شامل
- ✅ Git repository جاهز

## 📁 الملفات الرئيسية

```
jadoo-bot-latest/
├── bot_src/                    # البوت
│   ├── bot.py                  # الملف الرئيسي
│   ├── database/supabase_client.py  # عميل Supabase
│   ├── .env.example           # متغيرات البيئة
│   ├── Dockerfile             # للنشر
│   ├── railway.json           # إعدادات Railway
│   └── requirements.txt       # الاعتماديات
├── control/                   # لوحة التحكم
│   ├── src/                  # كود React
│   ├── Dockerfile            # للنشر
│   ├── railway.json          # إعدادات Railway
│   └── package.json          # الاعتماديات
├── DEPLOYMENT_GUIDE.md        # دليل النشر
└── README.md                 # هذا الملف
```

## 🚀 خطوات النشر

### 1. إعداد Supabase
1. إنشاء مشروع جديد
2. تنفيذ جداول SQL من `DEPLOYMENT_GUIDE.md`
3. الحصول على URL و Service Role Key

### 2. نشر البوت على Railway
1. New Project → Deploy from GitHub
2. إعدادات البيئة من `.env.example`
3. Railway سيقوم بالبناء والنشر تلقائياً

### 3. نشر لوحة التحكم
1. مشروع منفصل على Railway
2. ربط نفس مشروع Supabase

### 4. إعداد Webhook
```bash
curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://your-app-name.up.railway.app/webhook",
       "drop_pending_updates": true
     }'
```

## 🔑 متغيرات البيئة

انسخ `.env.example` إلى `.env` واملأ البيانات:

```bash
# Telegram
BOT_TOKEN=your_telegram_bot_token
ADMIN_TELEGRAM_ID=your_admin_id

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# Railway
WEBHOOK_URL=https://your-app.up.railway.app/webhook
PORT=8080
```

## 🛠️ التطوير المحلي

### تشغيل البوت:
```bash
cd bot_src
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

### تشغيل لوحة التحكم:
```bash
cd control
npm install
npm run dev
```

## 📊 المميزات

### البوت:
- 🔄 Webhook للإنتاج، Polling للتطوير
- 🗄️ Supabase لقاعدة البيانات
- 🔐 متغيرات بيئة آمنة
- 📝 Logging متكامل
- 🎮 معالجة المحادثات الكاملة

### لوحة التحكم:
- 📱 واجهة حديثة ومتجاوبة
- 🔄 Realtime updates
- 📊 إحصائيات وتقارير
- 🔧 إعدادات متقدمة
- 🎨 Dark/Light theme

## 🚨 استكشاف الأخطاء

### مشاكل شائعة:
1. **Webhook لا يعمل**: تحقق من Railway URL والـ Port
2. **الاتصال بـ Supabase**: تحقق من URL و Key
3. **Build Errors**: تحقق من requirements.txt

### الحلول:
- اتبع `DEPLOYMENT_GUIDE.md` خطوة بخطوة
- تحقق من جميع متغيرات البيئة
- استخدم health check endpoint

## 📞 الدعم

- **Railway**: https://docs.railway.app
- **Supabase**: https://docs.supabase.com
- **python-telegram-bot**: https://docs.python-telegram-bot.org

---

**ملاحظة**: المشروع جاهز بالكامل للنشر على Railway. جميع الإعدادات الأمنية والتقنية تم تطبيقها.
=======
# jadobot
Jado Bot And Admin Panel
>>>>>>> 9e0822b8cec8b496b1dc2bb9c0957a27c6d9e48b
