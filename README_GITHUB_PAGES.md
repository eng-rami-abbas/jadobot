# GitHub Pages Deployment

## رفع المشروع إلى GitHub Pages

1. ارفع جميع الملفات إلى مستودع GitHub.
2. ادخل إلى:
   Settings > Pages
3. اختر:
   Deploy from a branch
4. اختر:
   Branch: main
   Folder: /root
5. احفظ الإعدادات.

## إعداد API

قم بتعديل ملف:
config.js

وضع رابط الـ API الخاص بك:

window.WHEEL_API_URL = "https://YOUR_API_DOMAIN.com";

## مثال فتح Web App داخل البوت

https://YOUR_USERNAME.github.io/REPOSITORY_NAME/

أو مع API مخصص:

https://YOUR_USERNAME.github.io/REPOSITORY_NAME/?api=https://YOUR_API_DOMAIN.com
