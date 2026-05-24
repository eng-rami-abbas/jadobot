
const params = new URLSearchParams(window.location.search);
const API_BASE =
  params.get('api') ||
  window.WHEEL_API_URL ||
  '';

const DEMO_SEGMENTS = [
  '10$', '20$', '50$', '100$', '200$', '500$', 'Try Again'
];

export function getTelegramContext() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return { tg: null, userId: 'demo-user', initData: '' };

  try {
    tg.ready();
    tg.expand();
    tg.setHeaderColor('#0a0612');
    tg.setBackgroundColor('#0a0612');
  } catch(e) {}

  const userId = tg.initDataUnsafe?.user?.id
    ? String(tg.initDataUnsafe.user.id)
    : 'demo-user';

  return { tg, userId, initData: tg.initData || '' };
}

async function post(path, body) {
  if (!API_BASE) {
    return localDemoApi(path, body);
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json().catch(() => ({}));

    return {
      ok: res.ok,
      data,
      status: res.status
    };
  } catch (e) {
    return localDemoApi(path, body);
  }
}

function localDemoApi(path, body) {
  const lastSpin = localStorage.getItem('wheel_last_spin');
  const now = Date.now();

  if (path.includes('check-spin-eligibility')) {
    const canSpin = !lastSpin || (now - Number(lastSpin)) > 3000;

    return Promise.resolve({
      ok: true,
      status: 200,
      data: {
        eligible: canSpin,
        can_spin: canSpin
      }
    });
  }

  if (path.includes('spin-wheel')) {
    localStorage.setItem('wheel_last_spin', String(now));

    const reward =
      DEMO_SEGMENTS[Math.floor(Math.random() * DEMO_SEGMENTS.length)];

    return Promise.resolve({
      ok: true,
      status: 200,
      data: {
        success: true,
        reward,
        prize: reward,
        result: reward,
        result_id: Date.now().toString()
      }
    });
  }

  if (path.includes('claim-prize')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      data: {
        success: true
      }
    });
  }

  return Promise.resolve({
    ok: true,
    status: 200,
    data: {}
  });
}

export async function checkEligibility(userId, initData) {
  return post('/api/check-spin-eligibility', {
    telegram_id: userId,
    init_data: initData
  });
}

export async function spinWheel(userId, initData) {
  return post('/api/spin-wheel', {
    telegram_id: userId,
    init_data: initData
  });
}

export async function claimPrize(userId, initData, resultId) {
  return post('/api/claim-prize', {
    telegram_id: userId,
    init_data: initData,
    result_id: resultId
  });
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
