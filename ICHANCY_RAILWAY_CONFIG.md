# ⚙️ تكوين بيانات iChancy على Railway

## المشكلة: "Authentication failed" و "403 Forbidden"

هذا يعني أن بيانات الاعتماد غير صحيحة أو غير موجودة في Railway.

---

## ✅ الحل: تحديث متغيرات البيئة على Railway

### الخطوة 1: الذهاب إلى لوحة تحكم Railway

1. أدخل [railway.app](https://railway.app)
2. اختر المشروع: `jadobot`
3. اضغط على الخادم (Bot Service)

### الخطوة 2: الذهاب إلى Variables

```
Settings > Variables
```

### الخطوة 3: إضافة أو تحديث المتغيرات

تأكد من وجود هذه المتغيرات وأنها صحيحة:

| المتغير | القيمة | ملاحظات |
|--------|--------|---------|
| `ICHANCY_USERNAME` | بريدك الإلكتروني في ichancy | مثال: `agent@ichancy.com` |
| `ICHANCY_PASSWORD` | كلمة مرورك في ichancy | يجب أن تكون صحيحة تماماً |
| `PARENT_ID` | معرف الوكيل الأب | غالباً `2730826` |

### الخطوة 4: حفظ والنشر

بعد التحديث:
1. اضغط **Save**
2. Railway سيعيد بدء الخادم تلقائياً
3. تحقق من السجلات (Logs) للتأكد

---

## 🔍 كيفية الحصول على بيانات ichancy الصحيحة

### 1. الذهاب إلى agents.ichancy.com

```
https://agents.ichancy.com
```

### 2. إدخال بيانات الدخول

- **Username**: البريد الإلكتروني أو اسم المستخدم
- **Password**: كلمة المرور الصحيحة

### 3. التحقق من الأعمال

إذا تمكنت من الدخول = البيانات صحيحة ✅

---

## 🧪 فحص البيانات من اللوغ

ابحث في لوغ Railway عن:

```
❌ MISSING iChancy credentials in environment variables
   ICHANCY_USERNAME set: False
   ICHANCY_PASSWORD set: False
```

**الحل**: أضف المتغيرات

أو:

```
❌ Sign-in failed: 403 Forbidden
   Username used: agent@ichancy.com
```

**الحل**: تحقق من البيانات أنها صحيحة

---

## ⚠️ أسباب شائعة للخطأ 403

| السبب | الحل |
|------|------|
| كلمة المرور خاطئة | تحقق من كلمة المرور على ichancy.com |
| الحساب معطّل | تواصل مع دعم ichancy |
| البيانات مفقودة | تأكد من ملء المتغيرات على Railway |
| IP مُحجوب | تواصل مع دعم ichancy حول IP خادم Railway |

---

## 📱 رسالة الخطأ للمستخدم

إذا كانت البيانات خاطئة، سيرى المستخدم:

```
❌ خطأ في الاتصال بخوادم ichancy

السبب المحتمل:
• بيانات الدخول غير صحيحة
• تم تعطيل الحساب
• مشكلة في الاتصال

الحل:
تواصل مع الإدارة: @jadobotichancy
```

---

## ✅ التحقق من النجاح

بعد التحديث، ابحث في اللوغ عن:

```
✅ Successfully signed in to iChancy API
INFO - Registration successful! Player ID response: 12345
```

إذا رأيت هذا = كل شيء يعمل بشكل صحيح! 🎉

---

## 🆘 للمساعدة

إذا استمرت المشكلة:

1. تحقق من أن كلمة المرور لا تحتوي على أحرف خاصة معقدة
2. جرب نسخ البيانات مباشرة من ichancy.com
3. تأكد من عدم وجود مسافات زائدة
4. تواصل مع دعم ichancy للتأكد من أن الحساب نشط

---

## 📝 مثال عملي

```
ICHANCY_USERNAME = agent.name@company.com
ICHANCY_PASSWORD = SecurePass123!
PARENT_ID = 2730826
```

قم بنسخ هذا الشكل إلى Railway Variables.

---

**آخر تحديث**: May 13, 2026
