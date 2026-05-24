# ichancy Spin Wheel WebApp (no API)

واجهة العجلة جاهزة للعمل بدون API خارجي. ترفع على GitHub Pages وتفتح داخل Telegram Web App.

خطوات سريعة:
1. ادفع الملفات إلى الفرع `main`.
2. في إعدادات المستودع → Pages → اختر الفرع `main` و`/ (root)`.
3. افتح الرابط: https://<username>.github.io/<repo>/

ملاحظات مهمة للبوت:
- الواجهة ترسل النتيجة للبوت عبر `tg.sendData(JSON.stringify({ prize, user_id }))`.
- تأكد أن البوت لديك يتعامل مع تحديثات `web_app_data` (تلتقط الرسائل المرسلة من Web App وتتعامل معها).
- cooldown محلي مخزن في `localStorage` لكل مستخدم؛ هذا حل بسيط للاختبار فقط.