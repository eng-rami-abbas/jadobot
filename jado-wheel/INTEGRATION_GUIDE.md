# ===== JADO BOT - دليل ربط العجلة بالبوت الجاهز =====

## 📁 هيكل المشروع على GitHub Pages

```
jado-wheel/                    ← اسم repository على GitHub
├── index.html                 ← صفحة العجلة (WebApp)
├── style.css                  ← التنسيقات
├── config.js                  ← إعدادات العجلة
├── app.js                     ← منطق العجلة
├── background.png             ← خلفية (تضعها أنت)
└── assets/
    ├── logo.png               ← شعار JADO BOT
    ├── spin.png               ← زر SPIN
    ├── pointer.png            ← الدبوس المؤشر
    ├── sound.png              ← زر الصوت
    ├── spin.mp3               ← صوت الدوران
    ├── win.mp3                ← صوت الفوز
    └── tick.mp3               ← صوت التقطيع
```

---

## 🔗 خطوات الربط بالبوت الجاهز

### الخطوة 1: إعداد GitHub Pages

1. أنشئ repository جديد على GitHub باسم `jado-wheel`
2. ارفع جميع الملفات أعلاه + صورك
3. اذهب إلى Settings → Pages
4. اختر Branch: `main` / Folder: `/root`
5. احفظ الرابط (مثال: `https://yourname.github.io/jado-wheel/`)

---

### الخطوة 2: تعديل زر "اللفة المجانية" في بوتك

في كود البوت الجاهز، ابحث عن زر "اللفة المجانية" وعدله:

**قبل:**
```python
# زر اللفة المجانية القديم
keyboard = [
    [InlineKeyboardButton("🎰 اللفة المجانية", callback_data='free_spin')]
]
```

**بعد:**
```python
from telegram import WebAppInfo

WEB_APP_URL = "https://yourname.github.io/jado-wheel/"

# زر اللفة المجانية ← يفتح WebApp
keyboard = [
    [InlineKeyboardButton(
        "🎰 اللفة المجانية", 
        web_app=WebAppInfo(url=WEB_APP_URL)
    )]
]
```

---

### الخطوة 3: استقبال نتيجة العجلة في البوت

أضف handler لاستقبال البيانات من WebApp:

```python
from telegram.ext import MessageHandler, filters

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال نتيجة العجلة من WebApp"""

    if update.effective_message.web_app_data:
        data = json.loads(update.effective_message.web_app_data.data)

        if data.get('action') == 'wheel_spin_complete':
            user_id = data['user_id']
            result_type = data['result_type']
            result_label = data['result_label']
            result_value = data['result_value']

            # ✅ هنا تطبق المنطق الخاص بك:
            # 1. تحديث رصيد المستخدم في قاعدة البيانات
            # 2. تسجيل أنه استخدم تدويرته اليوم
            # 3. إرسال رسالة تأكيد للمستخدم

            result_text = f"""
🎰 <b>نتيجة عجلة الحظ</b>

الجائزة: {data.get('result_label')}
النوع: {result_type}

✅ تم تحديث حسابك!
            """

            await update.effective_message.reply_text(
                result_text, 
                parse_mode='HTML'
            )

            # 🔄 تحديث بيانات المستخدم في Supabase
            await update_user_after_spin(user_id, result_type, result_value)

# أضف الhandler
application.add_handler(
    MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA, 
        handle_webapp_data
    )
)
```

---

### الخطوة 4: التحقق من صلاحية اللفة قبل فتح العجلة

عند الضغط على زر "اللفة المجانية"، البوت يجب أن يتحقق:

```python
async def free_spin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عند الضغط على زر اللفة المجانية"""
    user = update.effective_user

    # ✅ تحقق من الشروط:
    # 1. هل أجرى إيداع اليوم؟
    has_deposit_today = await check_deposit_today(user.id)

    # 2. هل استخدم تدويرته اليوم؟
    has_spun_today = await check_spin_today(user.id)

    if not has_deposit_today:
        await update.message.reply_text(
            "❌ يجب إجراء إيداع أولاً للحصول على اللفة المجانية!

"
            "💰 اضغط على زر 'شحن رصيد'"
        )
        return

    if has_spun_today:
        await update.message.reply_text(
            "❌ لقد استخدمت تدويرتك اليوم!

"
            "📅 عد غداً بعد الإيداع للحصول على لفة جديدة."
        )
        return

    # ✅ كل الشروط متحققة → افتح العجلة
    keyboard = [
        [InlineKeyboardButton(
            "🎰 ابدأ اللف!",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )]
    ]

    await update.message.reply_text(
        "🎰 <b>عجلة الحظ جاهزة!</b>

"
        "اضغط الزر أدناه لفتح العجلة وربح جوائز رائعة!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
```

---

### الخطوة 5: تحديث قاعدة البيانات بعد اللفة

```python
async def update_user_after_spin(user_id, result_type, result_value):
    """تحديث بيانات المستخدم بعد اللفة"""

    today = date.today().isoformat()

    # تحديث: استخدم تدويرته اليوم
    await supabase.table('users').update({
        'spins_today': 1,
        'last_spin_date': today
    }).eq('user_id', user_id).execute()

    # تطبيق الجائزة
    if result_type == 'money':
        # إضافة رصيد
        await supabase.rpc('add_balance', {
            'p_user_id': user_id,
            'p_amount': result_value
        }).execute()

    elif result_type == 'bonus':
        # تخزين بونص للإيداع القادم
        await supabase.table('users').update({
            'pending_bonus': result_value
        }).eq('user_id', user_id).execute()

    elif result_type == 'respins':
        # إعادة تدوير: لا تخصم التدويرة
        await supabase.table('users').update({
            'spins_today': 0  # إعادة التدويرة
        }).eq('user_id', user_id).execute()

    elif result_type == 'lucky':
        # إضافة حظ أوفر
        await supabase.rpc('add_lucky_charm', {
            'p_user_id': user_id
        }).execute()

    elif result_type == 'premium':
        # تسجيل طلب تيليجرام بريميوم
        await supabase.table('users').update({
            'pending_premium': True
        }).eq('user_id', user_id).execute()

    # تسجيل في سجل اللفات
    await supabase.table('wheel_spins').insert({
        'user_id': user_id,
        'result_type': result_type,
        'result_label': result_label,
        'result_value': result_value,
        'created_at': datetime.now().isoformat()
    }).execute()
```

---

## 🎯 ملخص التدفق الكامل

```
[المستخدم] 
    ↓ يضغط "شحن رصيد"
    ↓ يتم الإيداع
    ↓ يضغط "اللفة المجانية"

[البوت] 
    ↓ يتحقق: هل أيدع اليوم؟ ✓
    ↓ يتحقق: هل لم يلف بعد؟ ✓
    ↓ يفتح WebApp (العجلة)

[WebApp - العجلة]
    ↓ المستخدم يضغط SPIN
    ↓ العجلة تدور
    ↓ تتوقف على قيمة
    ↓ ترسل النتيجة للبوت عبر sendData()
    ↓ تغلق WebApp

[البوت]
    ↓ يستقبل النتيجة
    ↓ يحدث قاعدة البيانات
    ↓ يخبر المستخدم بالنتيجة
    ↓ يمنع اللف مرة أخرى اليوم
```

---

## ⚠️ ملاحظات مهمة

1. **WebApp يعمل فقط داخل Telegram** - لا يمكن فتحه من المتصفح العادي
2. **sendData()** ترسل البيانات للبوت فقط عند إغلاق WebApp
3. **الصور** ضعها في مجلد `assets/` بنفس الأسماء المذكورة
4. **الأصوات** اختيارية - إذا لم توجد، ستعمل العجلة بدون صوت
5. **الخلفية** `background.png` تضعها أنت في المجلد الرئيسي

---

## 🚀 طريقة الرفع على GitHub Pages

```bash
# 1. أنشئ مجلد المشروع
mkdir jado-wheel
cd jado-wheel

# 2. انسخ جميع الملفات
# index.html, style.css, config.js, app.js
# assets/ (logo.png, spin.png, pointer.png, sound.png)
# background.png

# 3. أنشئ repository على GitHub
# اذهب إلى github.com وانشئ repository جديد

# 4. اربط المجلد المحلي بالـ repository
git init
git remote add origin https://github.com/YOUR_USERNAME/jado-wheel.git

# 5. ارفع الملفات
git add .
git commit -m "Initial wheel webapp"
git push -u origin main

# 6. فعّل GitHub Pages
# Settings → Pages → Source: Deploy from a branch
# Branch: main / folder: / (root)

# 7. انتظر 2-5 دقائق ثم افتح:
# https://YOUR_USERNAME.github.io/jado-wheel/
```

---

## 📋 قائمة الملفات المرفوعة

| الملف | الوصف |
|-------|-------|
| `index.html` | صفحة العجلة الرئيسية |
| `style.css` | تنسيقات CSS الفاخرة |
| `config.js` | إعدادات الأقسام والاحتمالات |
| `app.js` | منطق الدوران والنتائج |
| `supabase_schema.sql` | هيكل قاعدة البيانات |
| `integration_guide.md` | هذا الدليل |

---

## 🎨 الصور المطلوبة (تضعها أنت)

ضع هذه الصور في مجلد `assets/`:

| الصورة | المصدر | الوصف |
|--------|--------|-------|
| `logo.png` | صورتك 1000001131 | شعار JADO BOT |
| `spin.png` | صورتك 1000001132 | زر SPIN |
| `pointer.png` | صورتك 1000001133 | الدبوس المؤشر |
| `sound.png` | صورتك 1000001129 | زر الصوت |
| `background.png` | تختارها أنت | خلفية العجلة |

---

## 🔧 تخصيص العجلة

لتعديل احتمالات الجوائز، عدل في `config.js`:

```javascript
WEIGHTS: [
    0.20,  // 10000    - 20%
    0.15,  // 20000    - 15%
    0.15,  // حظ أوفر   - 15%
    0.05,  // بريميوم   - 5%
    0.15,  // بونص 5%   - 15%
    0.05,  // 50000    - 5%
    0.15,  // حظ أوفر   - 15%
    0.10   // إعادة تدوير - 10%
]
```

**المجموع يجب أن يكون = 1.00 (100%)**
