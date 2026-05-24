// wheel.js
const canvas = document.getElementById('wheelCanvas');
const ctx = canvas.getContext('2d');

// أبعاد العجلة
const WHEEL_SIZE = 400; // ستتغير مع resize
let wheelRadius, centerX, centerY;

// الأقسام (8 أقسام)
const SEGMENTS = ["10000","20000","حظ أوفر","Telegram Premium","50000","Bonus 5%","حظ أوفر","إعادة تدوير"];
const SEG_COUNT = 8;
const ARC = (2 * Math.PI) / SEG_COUNT;

// ألوان الأقسام (ذهبي/أسود)
const COLORS = [
  "#1a1a1a", "#b8960f", "#1a1a1a", "#b8960f",
  "#1a1a1a", "#b8960f", "#1a1a1a", "#b8960f"
];

// حالة الأنيميشن
let wheelAngle = 0;           // زاوية العجلة بالراديان
let isSpinning = false;
let spinVelocity = 0;
let ballAngle = 0;           // زاوية الكرة المطلقة (بالنسبة للشاشة)
let ballOnTrack = false;
let ballFalling = false;
let targetSegment = null;    // القسم المستهدف (من الخادم)

// متغيرات للكرة
let ballTrackRadius, ballPosX, ballPosY;
let ballDropProgress = 0;    // 0..1 هبوط الكرة نحو المركز
let ballBounce = 0;          // تأثير الاهتزاز الأخير

// مؤشر ثابت أعلى العجلة (12 o'clock)
const INDICATOR_ANGLE = -Math.PI/2; // يشير للأعلى

// ضبط الحجم
function resizeCanvas() {
  const container = canvas.parentElement;
  const size = Math.min(container.clientWidth, container.clientHeight);
  canvas.width = size * (window.devicePixelRatio || 1);
  canvas.height = size * (window.devicePixelRatio || 1);
  canvas.style.width = size + 'px';
  canvas.style.height = size + 'px';
  wheelRadius = size / 2.2;
  centerX = canvas.width / 2;
  centerY = canvas.height / 2;
  ballTrackRadius = wheelRadius * 0.92; // مسار خارجي
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// رسم العجلة
function drawWheel(angle) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(centerX, centerY);
  ctx.rotate(angle);

  // رسم الأقسام
  for (let i = 0; i < SEG_COUNT; i++) {
    const startAngle = i * ARC;
    const endAngle = startAngle + ARC;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, wheelRadius, startAngle, endAngle);
    ctx.closePath();
    // لون القسم
    ctx.fillStyle = COLORS[i];
    ctx.fill();
    ctx.strokeStyle = '#d4af37';
    ctx.lineWidth = 3;
    ctx.stroke();

    // كتابة النص
    ctx.save();
    ctx.rotate(startAngle + ARC/2);
    ctx.textAlign = "center";
    ctx.fillStyle = (COLORS[i] === '#1a1a1a') ? '#d4af37' : '#0a0a0a';
    ctx.font = `bold ${wheelRadius*0.15}px "Segoe UI"`;
    ctx.shadowColor = '#d4af37';
    ctx.shadowBlur = 6;
    ctx.fillText(SEGMENTS[i], wheelRadius*0.7, 8);
    ctx.restore();
  }

  // الحلقة الخارجية المعدنية
  ctx.beginPath();
  ctx.arc(0, 0, wheelRadius*1.02, 0, 2*Math.PI);
  ctx.strokeStyle = '#d4af37';
  ctx.lineWidth = 8;
  ctx.stroke();
  ctx.shadowColor = '#d4af37';
  ctx.shadowBlur = 15;
  ctx.stroke();

  // الفواصل المعدنية (تعكس الضوء)
  for (let i = 0; i < SEG_COUNT; i++) {
    const angle = i * ARC;
    const x1 = Math.cos(angle) * wheelRadius*0.85;
    const y1 = Math.sin(angle) * wheelRadius*0.85;
    const x2 = Math.cos(angle) * wheelRadius*0.95;
    const y2 = Math.sin(angle) * wheelRadius*0.95;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 3;
    ctx.stroke();
  }

  ctx.restore();

  // رسم المؤشر الثابت (مثلث)
  ctx.save();
  ctx.translate(centerX, centerY);
  ctx.beginPath();
  ctx.moveTo(0, -wheelRadius*0.98);
  ctx.lineTo(-15, -wheelRadius*1.08);
  ctx.lineTo(15, -wheelRadius*1.08);
  ctx.closePath();
  ctx.fillStyle = '#d4af37';
  ctx.shadowColor = '#d4af37';
  ctx.shadowBlur = 10;
  ctx.fill();
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.restore();

  // رسم الكرة إذا كانت ظاهرة
  if (ballOnTrack) {
    drawBall();
  }
}

function drawBall() {
  // حساب موضع الكرة على المسار الخارجي (ثابت بالنسبة للشاشة)
  let x = centerX + Math.cos(ballAngle) * ballTrackRadius;
  let y = centerY + Math.sin(ballAngle) * ballTrackRadius;

  // أثناء الهبوط نحرك الكرة تدريجياً نحو المركز
  if (ballFalling) {
    const dropRadius = ballTrackRadius - ballDropProgress * (ballTrackRadius - wheelRadius*0.7);
    x = centerX + Math.cos(ballAngle) * dropRadius;
    y = centerY + Math.sin(ballAngle) * dropRadius;
    // اهتزاز ارتطام
    x += Math.sin(ballBounce * 20) * (1 - ballDropProgress) * 8;
    y += Math.cos(ballBounce * 23) * (1 - ballDropProgress) * 8;
  }

  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, 12, 0, 2*Math.PI);
  const gradient = ctx.createRadialGradient(x-4, y-4, 2, x, y, 12);
  gradient.addColorStop(0, '#fff');
  gradient.addColorStop(0.5, '#e6c85a');
  gradient.addColorStop(1, '#b8960f');
  ctx.fillStyle = gradient;
  ctx.shadowColor = '#d4af37';
  ctx.shadowBlur = 15;
  ctx.fill();
  ctx.restore();
}

// دالة بدء الأنيميشن
function startSpinAnimation(targetSegIndex) {
  if (isSpinning) return;
  isSpinning = true;
  targetSegment = targetSegIndex;
  ballOnTrack = true;
  ballFalling = false;
  ballDropProgress = 0;
  ballBounce = 0;

  // حساب الزاوية النهائية للعجلة بحيث يصبح المؤشر على القسم المستهدف
  const targetAngleOffset = - (targetSegIndex * ARC + ARC/2); // مركز القسم
  // نضيف دورات عشوائية (3-5 دورات)
  const fullRotations = (3 + Math.floor(Math.random()*3)) * 2 * Math.PI;
  const finalAngle = fullRotations + targetAngleOffset;

  // سرعة دوران العجلة (تبدأ سريعة وتتباطأ)
  spinVelocity = 0.25; // راديان لكل إطار
  const targetAngleFinal = finalAngle;

  // صوت البدء
  SoundManager.playSpinStart();

  // الكرة تبدأ من زاوية عشوائية بعكس اتجاه العجلة
  ballAngle = Math.random() * 2 * Math.PI;
  let ballSpeed = -0.3; // عكس اتجاه العجلة

  // تحديث الأنيميشن
  function animate() {
    if (!isSpinning) return;

    // تحديث زاوية العجلة
    if (Math.abs(spinVelocity) > 0.0005) {
      wheelAngle += spinVelocity;
      // تباطؤ العجلة
      spinVelocity *= 0.995;
      // إيقاف العجلة عند الزاوية النهائية المطلوبة تقريبًا
      if (Math.abs(spinVelocity) < 0.0005) {
        wheelAngle = finalAngle; // تثبيت
        spinVelocity = 0;
      }
    }

    // تحديث الكرة (المرحلة الأولى: دوران على المسار الخارجي)
    if (ballOnTrack && !ballFalling) {
      ballAngle += ballSpeed;
      // تباطؤ الكرة تدريجياً
      ballSpeed *= 0.998;
      // صوت احتكاك خفيف
      if (Math.random() < 0.1) SoundManager.playClick();

      // شرط بدء السقوط: عندما تبطئ الكرة وتقترب من زاوية الهدف
      const angleDiff = normalizeAngle(ballAngle - (finalAngle - wheelAngle));
      if (Math.abs(ballSpeed) < 0.05 && Math.abs(angleDiff) < 0.3) {
        ballFalling = true;
        ballSpeed = 0;
      }
    }

    // المرحلة الثانية: هبوط الكرة
    if (ballFalling) {
      ballDropProgress += 0.02;
      ballBounce += 0.1;
      // صوت ارتطام بالفواصل
      if (ballDropProgress % 0.15 < 0.02) SoundManager.playClick();
      // عند اكتمال الهبوط
      if (ballDropProgress >= 1) {
        ballDropProgress = 1;
        ballFalling = false;
        ballOnTrack = false;
        isSpinning = false;
        // استدعاء دالة إظهار النتيجة بعد ثبات الكرة
        onSpinComplete(targetSegment);
        return;
      }
    }

    drawWheel(wheelAngle);
    requestAnimationFrame(animate);
  }

  animate();
}

// تطبيع الزاوية بين -PI و PI
function normalizeAngle(angle) {
  while (angle > Math.PI) angle -= 2*Math.PI;
  while (angle < -Math.PI) angle += 2*Math.PI;
  return angle;
}

// رسم أولي
drawWheel(0);