const params = new URLSearchParams(window.location.search);
const API_BASE = params.get('api') || window.WHEEL_API_URL || window.location.origin;

export function getTelegramContext() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return { tg: null, userId: null, initData: '' };
  tg.ready();
  tg.expand();
  tg.setHeaderColor('#0a0612');
  tg.setBackgroundColor('#0a0612');
  const userId = tg.initDataUnsafe?.user?.id
    ? String(tg.initDataUnsafe.user.id)
    : new URLSearchParams(location.search).get('user_id');
  return { tg, userId, initData: tg.initData || '' };
}

async function post(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok && !data.message) {
    data.message = data.message || 'خطأ في الاتصال بالسيرفر';
  }
  return { ok: res.ok, data, status: res.status };
}

export async function checkEligibility(userId, initData) {
  return post('/api/check-spin-eligibility', { telegram_id: userId, init_data: initData });
}

export async function spinWheel(userId, initData) {
  return post('/api/spin-wheel', { telegram_id: userId, init_data: initData });
}

export async function claimPrize(userId, initData, resultId) {
  return post('/api/claim-prize', { telegram_id: userId, init_data: initData, result_id: resultId });
}

export function sendToBot(tg, payload) {
  if (!tg) return;
  try {
    tg.sendData(JSON.stringify(payload));
    setTimeout(() => tg.close(), 500);
  } catch (e) {
    console.warn('sendData failed', e);
  }
}
