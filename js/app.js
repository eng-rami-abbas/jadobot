// app.js
let currentBalance = 0;
let freeSpinsRemaining = 0;
let bonusActive = false;
let bonusPercent = 5;

// تهيئة الصفحة
async function initApp() {
  // قراءة بيانات المستخدم من Supabase أو إنشاء حساب
  const { data: user, error } = await supabase
    .from('users')
    .select('*')
    .eq('telegram_id', telegramUser.id)
    .single();

  if (error && error.code !== 'PGRST116') {
    console.error(error);
    return;
  }

  if (!user) {
    // تسجيل جديد
    const { data: newUser, error: insertError } = await supabase
      .from('users')
      .insert([{ 
        telegram_id: telegramUser.id,
        username: telegramUser.username,
        first_name: telegramUser.first_name,
        balance: 0,
        free_spins_remaining: 0,
        bonus_active: false,
        bonus_percentage: 5,
        last_spin_date: null
      }])
      .select()
      .single();
    if (insertError) { console.error(insertError); return; }
    updateUI(newUser);
  } else {
    updateUI(user);
  }

  // التحقق من وجود تدويرة مجانية متبقية (إعادة تدوير)
  freeSpinsRemaining = user?.free_spins_remaining || 0;

  // تعطيل الزر إذا لم يكن مؤهلاً (سيتم فحصه عند النقر)
  document.getElementById('spinButton').addEventListener('click', handleSpin);
}

function updateUI(user) {
  currentBalance = user.balance;
  document.getElementById('balance').textContent = currentBalance;
  if (user.bonus_active) {
    bonusActive = true;
    bonusPercent = user.bonus_percentage || 5;
    // يمكن عرض شارة
  }
}

async function handleSpin() {
  if (isSpinning) return;

  // التحقق من الأهلية عبر Edge Function (التحقق من الإيداعات والحد اليومي)
  try {
    const eligibility = await callEdgeFunction('spin-wheel', {
      telegram_id: telegramUser.id,
      action: 'check_eligibility'
    });

    if (!eligibility.allowed) {
      alert(eligibility.message || 'لا يمكنك التدوير حالياً');
      return;
    }

    // تعطيل الزر
    document.getElementById('spinButton').classList.add('disabled');
    document.getElementById('spinButton').querySelector('.spin-text').style.display = 'none';
    // إظهار الكرة (ستتولى wheel.js إظهارها)
    document.getElementById('ball').classList.add('ball-visible');

    // استدعاء Edge Function لتحديد الجائزة (المنطق الآمن)
    const result = await callEdgeFunction('spin-wheel', {
      telegram_id: telegramUser.id,
      action: 'spin'
    });

    // النتيجة تحتوي على segment_index والجائزة والمبلغ وغيرها
    const { segment_index, prize_type, prize_value, message } = result;

    // تشغيل أنيميشن الهبوط على القسم المحدد
    startSpinAnimation(segment_index);

    // عند اكتمال الأنيميشن سيتم استدعاء onSpinComplete (معرف في wheel.js)
    window.pendingSpinResult = { prize_type, prize_value, message };

  } catch (error) {
    alert('حدث خطأ، حاول مرة أخرى');
    console.error(error);
    resetSpinButton();
  }
}

// تُستدعى من wheel.js بعد استقرار الكرة
function onSpinComplete(segmentIndex) {
  const result = window.pendingSpinResult;
  if (!result) return;
  
  const { prize_type, prize_value, message } = result;
  
  // عرض رسالة النتيجة
  showResult(message);
  
  // تحديث الرصيد محلياً (القيمة الفعلية تُحدث في الـ Edge Function)
  if (prize_type === 'money') {
    currentBalance += prize_value;
    document.getElementById('balance').textContent = currentBalance;
    SoundManager.playWin();
  } else if (prize_type === 'bonus') {
    bonusActive = true;
    SoundManager.playWin();
  } else if (prize_type === 'free_spin') {
    freeSpinsRemaining++;
    SoundManager.playWin();
  } else if (prize_type === 'premium') {
    SoundManager.playWin();
  } else if (prize_type === 'lose') {
    SoundManager.playLose();
  }

  // إرسال رسالة تيليجرام عبر Edge Function
  callEdgeFunction('send-message', {
    telegram_id: telegramUser.id,
    text: message
  }).catch(console.error);

  // إعادة تعيين الزر بعد 3 ثواني
  setTimeout(resetSpinButton, 3000);
}

function showResult(msg) {
  const msgDiv = document.getElementById('resultMessage');
  msgDiv.textContent = msg;
  msgDiv.classList.remove('hidden');
  setTimeout(() => msgDiv.classList.add('hidden'), 4000);
}

function resetSpinButton() {
  const btn = document.getElementById('spinButton');
  btn.classList.remove('disabled');
  btn.querySelector('.spin-text').style.display = 'block';
  document.getElementById('ball').classList.remove('ball-visible');
  // إيقاف أي أنيميشن متبقية
  isSpinning = false;
  ballOnTrack = false;
  ballFalling = false;
  drawWheel(wheelAngle);
}

// بدء التطبيق
initApp();