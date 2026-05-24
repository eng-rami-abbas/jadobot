// telegram.js
const tg = window.Telegram.WebApp;
tg.expand(); // ملء الشاشة بالكامل
tg.enableClosingConfirmation(); // تأكيد الخروج

let telegramUser = null;
if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
  telegramUser = {
    id: tg.initDataUnsafe.user.id,
    username: tg.initDataUnsafe.user.username || "",
    first_name: tg.initDataUnsafe.user.first_name || "لاعب"
  };
} else {
  // وضع الاختبار بدون تيليجرام
  telegramUser = {
    id: 123456789,
    username: "test_user",
    first_name: "Test"
  };
}

// تعيين اسم المستخدم في الواجهة
document.getElementById('username').textContent = 
  telegramUser.first_name + (telegramUser.username ? ' (@'+telegramUser.username+')' : '');