# JADO BOT — Luxury Roulette (Telegram Web App)

## Features
- 8-segment gold casino wheel (server-authoritative outcomes)
- Vertical showcase → real roulette mode on SPIN
- Ball physics (opposite wheel rotation, deceleration, pocket bounce)
- Procedural sound effects + mute toggle
- Supabase: deposits, spins, results, bonuses, premium queue
- Telegram WebApp SDK integration

## Deploy on Railway
1. Create service from `wheel_project/`
2. Set env: `SUPABASE_URL`, `SUPABASE_KEY` (service role), `TELEGRAM_BOT_TOKEN`
3. Run SQL: `supabase_roulette_schema.sql` in Supabase

## Bot env
```env
WHEEL_WEBAPP_URL=https://YOUR-RAILWAY-APP.up.railway.app/
```

## API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/check-spin-eligibility` | POST | Can user spin? |
| `/api/spin-wheel` | POST | Server picks prize + angle |
| `/api/claim-prize` | POST | Apply prize to balance/DB |
| `/api/save-result` | POST | Alias of claim |

Body: `{ "init_data": "<Telegram.WebApp.initData>", "telegram_id": "..." }`

## Static + API same origin
Open `index.html` via Railway URL inside Telegram Web App button.
