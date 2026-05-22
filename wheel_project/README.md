# 🎡 عجلة الروليت الاحترافية - Ichancy Yuki

## المميزات

- ✅ **عجلة روليت ثلاثية الأبعاد** - العجلة تنام (تصبح مسطحة) أثناء الدوران
- ✅ **كرة روليت حقيقية** - كرة تدور حول العجلة وتتوقف على القطاع الفائز
- ✅ **لا سهم** - النتيجة تحددها الكرة مثل الروليت الحقيقي
- ✅ **Supabase** - قاعدة بيانات احترافية
- ✅ **شروط اللعب** - إيداع يومي + لعب مرة واحدة فقط
- ✅ **بونص متراكم** - يُطبق عند الشحن القادم
- ✅ **لفة تجريبية** - للتجربة بدون حفظ

## الملفات

| الملف | الوصف |
|-------|--------|
| `server.py` | سيرفر Flask مع Supabase |
| `wheel.html` | واجهة العجلة |
| `index.html` | نقطة دخول الواجهة في GitHub Pages |
| `wheel.js` | منطق العجلة (كرة روليت + 3D) |
| `style.css` | تصميم العجلة |
| `back.jpg` | خلفية الكازينو |
| `pin.png` | صورة الدبوس (اختياري) |
| `requirements.txt` | مكتبات Python |
| `Procfile` | إعدادات Render |
| `.env.example` | نموذج المتغيرات |
| `supabase_schema.sql` | هيكل قاعدة البيانات |

## 🚀 التشغيل

### 1. إعداد Supabase

1. أنشئ مشروع على [supabase.com](https://supabase.com)
2. افتح SQL Editor
3. انسخ محتوى `supabase_schema.sql` ونفذه
4. اذهب إلى Project Settings → API
5. انسخ `URL` و `anon public` key

### 2. الاستضافة على Render (مجاني)

1. أنشئ حساب على [render.com](https://render.com)
2. New Web Service → Build from GitHub
3. ارفع الملفات (أو ربط GitHub)
4. في Environment Variables أضف:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```
5. Render يقرأ `Procfile` تلقائياً

### 3. التشغيل المحلي

```bash
# تثبيت المكتبات
pip install -r requirements.txt

# إعداد المتغيرات
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-anon-key

# التشغيل
python server.py
```

## 🔗 ربط بوت Telegram

```python
from telegram import WebAppInfo, InlineKeyboardButton

btn = InlineKeyboardButton(
    "🎡 العجلة",
    web_app=WebAppInfo(url=f"https://your-app.onrender.com/wheel.html?user_id={user_id}")
)
```

## 📡 API Endpoints

| Endpoint | Method | وصف |
|----------|--------|-----|
| `/check` | POST | التحقق من صلاحية الدوران |
| `/spin` | POST | تنفيذ الدوران وحفظ النتيجة |
| `/deposit` | POST | تسجيل إيداع (للبوت) |
| `/user/<id>` | GET | جلب بيانات المستخدم |
| `/stats/<id>` | GET | إحصائيات المستخدم |

### مثال: تسجيل إيداع

```bash
curl -X POST https://your-app.onrender.com/deposit   -H "Content-Type: application/json"   -d '{"user_id": "123456", "amount": 50000, "currency": "SYP"}'
```

### مثال: جلب بيانات المستخدم

```bash
curl https://your-app.onrender.com/user/123456
```

## 🎨 كيف تعمل الكرة

1. عند الضغط على الزر: العجلة تُمال (rotateX) لتصبح مسطحة
2. الكرة تُرمى من خارج اللقطة إلى حافة العجلة
3. الكرة تدور عكس عقارب الساعة حول العجلة
4. تتباطأ الكرة تدريجياً وتسقط إلى القطاع الفائز
5. العجلة تعود للوضع العمودي بعد التوقف
6. تُعرض النتيجة في صندوق ملون

## ⚠️ ملاحظات

- ملف `back.jpg` مطلوب - خلفية الكازينو
- ملف `pin.png` اختياري - إذا لم يوجد يستخدم SVG
- الكرة تُرسم ديناميكياً بـ CSS + JavaScript
- جميع الألوان والقطاعات قابلة للتخصيص عبر JSON
