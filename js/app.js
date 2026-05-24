import { SEGMENTS } from './segments.js';
import { getTelegramContext, checkEligibility, spinWheel, claimPrize, sendToBot } from './api.js';
import { RouletteAudio } from './audio.js';
import { WheelRenderer } from './renderer.js';
import { SpinPhysics } from './physics.js';

const $ = (id) => document.getElementById(id);

const loader = $('loader');
const loaderBar = $('loaderBar');
const app = $('app');
const wheelAssembly = $('wheelAssembly');
const wheelCanvas = $('wheelCanvas');
const spinBtn = $('spinBtn');
const statusMsg = $('statusMsg');
const resultPanel = $('resultPanel');
const rouletteBowl = $('rouletteBowl');
const ball = $('ball');
const soundToggle = $('soundToggle');
const toast = $('toast');

const audio = new RouletteAudio();
const renderer = new WheelRenderer(wheelCanvas);
const { tg, userId, initData } = getTelegramContext();

let pendingSpin = null;
let animating = false;

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 2800);
}

function setStatus(msg) {
  statusMsg.textContent = msg || '';
}

function setResult(html, isWin) {
  resultPanel.innerHTML = html;
  resultPanel.classList.toggle('win', !!isWin);
  resultPanel.classList.remove('hidden');
}

async function boot() {
  let p = 0;
  const iv = setInterval(() => {
    p = Math.min(p + 12, 100);
    loaderBar.style.width = `${p}%`;
    if (p >= 100) clearInterval(iv);
  }, 120);

  if (!userId) {
    setStatus('⚠️ افتح اللعبة من بوت Telegram');
    spinBtn.disabled = true;
  } else {
    const { ok, data } = await checkEligibility(userId, initData);
    if (ok && data.allowed) {
      spinBtn.disabled = false;
      setStatus(data.message || 'اضغط SPIN للتدوير');
      if (data.extra_spins > 0) {
        setStatus(`🔄 لديك ${data.extra_spins} لفة إضافية`);
      }
    } else {
      spinBtn.disabled = true;
      setStatus(data.message || 'غير متاح للتدوير حالياً');
    }
  }

  await new Promise((r) => setTimeout(r, 1400));
  loader.classList.add('hidden');
  app.classList.remove('hidden');
  wheelAssembly.classList.add('showcase');
  resize();
  loop();
}

function resize() {
  renderer.resize();
  positionBall(0, 0);
}

function loop() {
  renderer.draw();
  requestAnimationFrame(loop);
}

function positionBall(angleRad, progress) {
  const assembly = wheelAssembly.getBoundingClientRect();
  const cx = assembly.left + assembly.width / 2;
  const cy = assembly.top + assembly.height / 2;
  const rim = assembly.width / 2 - 6;
  const r = rim * (0.92 - progress * 0.12);
  const x = cx + Math.cos(angleRad) * r;
  const y = cy + Math.sin(angleRad) * r;
  ball.style.left = `${x}px`;
  ball.style.top = `${y}px`;
}

function enterRouletteMode() {
  wheelAssembly.classList.remove('showcase');
  wheelAssembly.classList.add('roulette-mode');
  rouletteBowl.classList.remove('hidden');
  ball.classList.remove('hidden');
  spinBtn.classList.add('hidden');
}

async function handleSpin() {
  if (animating || !userId) return;
  animating = true;
  spinBtn.disabled = true;
  resultPanel.classList.add('hidden');

  audio.spinStart();
  setStatus('⏳ جاري التحضير...');

  const { ok, data } = await spinWheel(userId, initData);
  if (!ok || !data.success) {
    animating = false;
    spinBtn.disabled = false;
    setStatus(data.message || 'فشل التدوير');
    showToast(data.message || 'خطأ');
    return;
  }

  pendingSpin = data;
  enterRouletteMode();
  setStatus('🎰 الروليت يدور...');

  const physics = new SpinPhysics({
    onWheel: (deg) => renderer.setRotation(deg),
    onBall: (rad, t) => positionBall(rad, t),
    onTick: () => audio.ballTick(),
    onBounce: () => audio.ballBounce(),
    onComplete: () => finishSpin(data),
  });

  physics.start(data.target_angle, 11000);
}

async function finishSpin(spinData) {
  const prize = spinData.prize || {};
  const seg = SEGMENTS[spinData.segment_index] || SEGMENTS[0];

  const { ok, data: claim } = await claimPrize(userId, initData, spinData.result_id);
  const msg = claim.telegram_message || claim.message || '';

  const isWin = ['cash', 'bonus', 'premium', 'respin'].includes(prize.type);
  if (isWin) {
    audio.win();
    if (typeof confetti === 'function') {
      confetti({ particleCount: 120, spread: 70, origin: { y: 0.55 } });
    }
  } else {
    audio.lose();
  }

  setResult(msg.replace(/\n/g, '<br>'), isWin);
  setStatus('');

  sendToBot(tg, {
    prize: {
      type: prize.type,
      code: prize.code,
      amount: prize.amount,
      percent: prize.percent,
      label_ar: prize.label_ar || seg.labelAr,
    },
    result_id: spinData.result_id,
  });

  animating = false;
  if (prize.type === 'respin' && claim.success) {
    spinBtn.classList.remove('hidden');
    spinBtn.disabled = false;
    wheelAssembly.classList.add('showcase');
    wheelAssembly.classList.remove('roulette-mode');
    rouletteBowl.classList.add('hidden');
    ball.classList.add('hidden');
    setStatus('🔄 لديك لفة إضافية! اضغط SPIN');
  }
}

soundToggle.addEventListener('click', () => {
  audio.setEnabled(!audio.enabled);
  soundToggle.classList.toggle('muted', !audio.enabled);
  soundToggle.querySelector('.sound-icon').textContent = audio.enabled ? '🔊' : '🔇';
});

spinBtn.addEventListener('click', handleSpin);
window.addEventListener('resize', resize);

boot();
