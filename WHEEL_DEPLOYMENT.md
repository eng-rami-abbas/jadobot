# تعليمات رفع وتشغيل زر اللفة المجانية

## ملخص الملفات المطلوبة

تم نقل ملفات العجلة إلى الموقع الصحيح:
- `wheel_project/index.html` - صفحة العجلة الرئيسية
- `wheel_project/back.jpg` - صورة الخلفية
- `wheel_project/pin.png` - صورة المؤشر
- `wheel_project/spin.mp3` - صوت الدوران
- `wheel_project/wheel.html` - واجهة العجلة الاحتياطية

## الخطوة 1: إعداد Supabase

1. افتح ملف `WHEEL_SETUP.md` واتبع التعليمات لإنشاء جدول `wheel_spins` في Supabase
2. تأكد من أن الجدول تم إنشاؤه بنجاح

## الخطوة 2: إعداد متغيرات البيئة

1. افتح ملف `bot_src/.env`
2. أضف السطر التالي مع استبدال الرابط برابط GitHub Pages الخاص بك:

```env
WHEEL_WEBAPP_URL=https://yourusername.github.io/jadoo-bot-latest/wheel_project/
```

## الخطوة 3: رفع الملفات على GitHub

### الخيار A: استخدام GitHub Pages (موصى به)

1. تأكد أن ملفات العجلة موجودة في مجلد `wheel_project/` في root المشروع
2. ادفع الملفات إلى GitHub:

```bash
git add wheel_project/
git commit -m "Add wheel web app files"
git push origin main
```

3. في GitHub، اذهب إلى إعدادات المستودع (Settings)
4. اختر **Pages** من القائمة الجانبية
5. في قسم **Build and deployment**:
   - Source: اختر **Deploy from a branch**
   - Branch: اختر **main**
   - Folder: اختر **/ (root)**
6. اضغط **Save**

7. انتظر بضع دقائق حتى يتم نشر الموقع
8. سيكون الرابط: `https://eng-rami-abbas.github.io/jadobot/wheel_project/`

### الخيار B: استخدام فرع gh-pages

```bash
# إنشاء فرع gh-pages
git checkout --orphan gh-pages
git rm -rf .

# نسخ ملفات العجلة فقط
cp -r wheel_project/* .
git add .
git commit -m "Initial wheel app"
git push origin gh-pages

# العودة للفرع الرئيسي
git checkout main
```

## الخطوة 4: تحديث رابط Web App

بعد الحصول على رابط GitHub Pages:

1. عدّل ملف `bot_src/.env`:
```env
WHEEL_WEBAPP_URL=https://yourusername.github.io/jadoo-bot-latest/wheel_project/
```

2. إذا كنت تستخدم Railway أو أي منصة استضافة أخرى، أضف المتغير هناك أيضاً

## الخطوة 5: تشغيل البوت

### محلياً:

```bash
cd bot_src
python bot.py
```

### على Railway:

1. ادفع التغييرات إلى GitHub
2. Railway سيقوم بإعادة النشر تلقائياً
3. تأكد من إضافة متغير `WHEEL_WEBAPP_URL` في إعدادات Railway

## الخطوة 6: الاختبار

1. افتح البوت في Telegram
2. اضغط على زر **اللفة المجانية 🎡**
3. سيفتح Web App مع العجلة
4. اضغط على زر الدوران
5. بعد انتهاء الدوران، سيتم إرسال النتيجة للبوت
6. سيتم تسجيل وقت اللفة في Supabase
7. المحاولة التالية ستكون متاحة بعد 24 ساعة

## ملاحظات مهمة

- **قاعدة البيانات**: يتم استخدام Supabase حصرياً لتخزين بيانات اللفات (cooldown)
- **لا توجد قواعد بيانات محلية**: جميع البيانات مخزنة في Supabase
- **Cooldown**: كل مستخدم لديه لفة مجانية كل 24 ساعة
- **Web App**: تعمل بدون API خارجي، فقط Telegram Web App API

## استكشاف الأخطاء

### العجلة لا تفتح:
- تأكد من رابط `WHEEL_WEBAPP_URL` صحيح
- تأكد من أن GitHub Pages يعمل
- تحقق من console في المتصفح للأخطاء

### Cooldown لا يعمل:
- تأكد من أن جدول `wheel_spins` موجود في Supabase
- تحقق من صلاحيات الجدول
- تأكد من أن متغيرات Supabase صحيحة في `.env`

### البيانات لا تُرسل للبوت:
- تأكد من أن handler `handle_web_app_data` مضاف في `bot.py`
- تحقق من logs البوت للأخطاء
- تأكد من أن Web App يستخدم `tg.sendData()` بشكل صحيح
