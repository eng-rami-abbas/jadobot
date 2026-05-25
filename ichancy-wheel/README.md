# 🎰 JADO BOT - Premium Roulette Experience

## نظرة عامة
عجلة روليت فاخرة ثلاثية الأبعاد داخل Telegram Web App مع فيزياء واقعية وتأثيرات سينمائية.

## 📁 بنية المشروع

```
jado_roulette/
├── index.html              # الصفحة الرئيسية
├── admin.html              # لوحة الإدارة
├── style.css               # التنسيقات
├── js/
│   ├── main.js             # متحكم التطبيق الرئيسي
│   ├── wheel.js            # محرك العجلة 3D (Three.js)
│   ├── physics.js          # فيزياء الكرة
│   ├── telegram.js         # تكامل Telegram WebApp
│   ├── supabase.js         # تكامل Supabase
│   └── audio.js            # نظام الصوت (Howler.js)
├── assets/
│   └── jado.png            # خلفية JADO
├── audio/
│   ├── spin.mp3            # صوت الدوران
│   ├── ball.mp3            # صوت الكرة
│   ├── bounce.mp3          # صوت الارتطام
│   ├── win.mp3             # صوت الفوز
│   ├── lose.mp3            # صوت الخسارة
│   └── ambient.mp3         # موسيقى الخلفية
└── supabase/
    ├── setup.sql           # إعداد قاعدة البيانات
    └── functions/
        └── get-spin-result/
            └── index.ts    # Edge Function للنتائج الآمنة
```

## 🚀 التثبيت والتشغيل

### 1. GitHub Pages
```bash
# رفع المشروع إلى GitHub
# Settings > Pages > Source: Deploy from a branch > main
```

### 2. Supabase Setup
1. أنشئ مشروع جديد في Supabase
2. افتح SQL Editor
3. انسخ محتوى `supabase/setup.sql` ونفذه
4. احصل على `URL` و `anon key`
5. عدل `js/supabase.js` ببياناتك

### 3. Supabase Edge Function (اختياري - موصى به)
```bash
# تثبيت Supabase CLI
npm install -g supabase

# تسجيل الدخول
supabase login

# ربط المشروع
supabase link --project-ref your-project-ref

# نشر الـ Edge Function
supabase functions deploy get-spin-result

# إضافة المتغيرات البيئية
supabase secrets set SUPABASE_URL=your-url
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your-service-key
```

### 4. Telegram Bot Setup
```
1. أنشئ بوت جديد في @BotFather
2. فعّل Web App: /setinline → Choose your bot → Enable
3. أرسل رابط GitHub Pages كـ Web App URL
4. استخدم الأمر: /setmenubutton
```

## 🎮 آلية اللعب

### الشروط
- يجب على المستخدم الإيداع أولاً
- تدويرة واحدة يومياً كحد أقصى
- التدويرات المجانية من "إعادة تدوير" لا تحسب ضمن الحد اليومي

### الجوائز
| الجائزة | النتيجة |
|---------|---------|
| 10000 | إضافة مباشرة للرصيد |
| 20000 | إضافة مباشرة للرصيد |
| 50000 | إضافة مباشرة للرصيد |
| Telegram Premium | إنشاء سجل pending |
| Bonus 5% | بونص على الإيداع القادم |
| إعادة تدوير | تدويرة مجانية إضافية |
| حظ أوفر | لا جائزة |

## 🛡️ الأمان

- ❌ **ممنوع** استخدام `Math.random()` في الواجهة
- ✅ النتائج تأتي من Supabase Backend فقط
- ✅ Edge Function تستخدم `crypto.getRandomValues()`
- ✅ Row Level Security على جميع الجداول
- ✅ التحقق من الإيداع قبل كل تدويرة

## 🎨 التأثيرات السينمائية

### المرحلة 1: الاهتزاز
- اهتزاز خفيف للعجلة
- صوت خلفي منخفض

### المرحلة 2: الوميض الذهبي
- وميض LED Ring
- تأثير إضاءة ذهبية

### المرحلة 3: تكبير الكاميرا
- تقريب تدريجي
- تركيز على العجلة

### المرحلة 4: الميلان للأفقي
- GSAP + Three.js
- انتقال سلس من Vertical إلى Horizontal

### المرحلة 5: تحول الزر إلى كرة
- Morph Animation
- ظهور كرة الروليت

## 🔧 التخصيص

### تغيير الألوان
```css
:root {
    --gold-primary: #FFD700;
    --red-dark: #8B0000;
    --purple-royal: #4B0082;
}
```

### تغيير الجوائز
```javascript
// js/wheel.js
this.segments = [
    { name: 'Your Prize', color: '#yourColor', icon: '🔥' },
    // ...
];
```

### تغيير الأصوات
استبدل الملفات في مجلد `audio/` بأصواتك الخاصة.

## 📱 التوافق

- ✅ Android (Chrome)
- ✅ iPhone (Safari)
- ✅ Telegram WebApp
- ✅ 60FPS على الأجهزة المتوسطة

## 📝 الترخيص

MIT License - JADO BOT

## 🤝 الدعم

للدعم والاستفسارات:
- Telegram: @JADO_BOT
- GitHub Issues

---

**صُنع بإتقان لـ JADO BOT 🎰👑**
