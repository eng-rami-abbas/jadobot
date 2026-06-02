# Jadoo Bot - Setup Guide

## Environment Variables

Create a `.env` file in the bot folder with:

```
BOT_TOKEN=your_telegram_bot_token
SUPABASE_URL=https://vszunhzxcdedcasiauza.supabase.co
SUPABASE_KEY=your_supabase_SERVICE_ROLE_key
```

**Important:** Use the **Service Role** key from Supabase (not the anon key).
Find it in: Supabase Dashboard → Project Settings → API → service_role key

## Install Dependencies

```bash
pip install -r requirements.txt
```

Make sure `supabase` is in requirements.txt:
```
python-telegram-bot
supabase
python-dotenv
pytz
httpx
```

## Run the Bot

```bash
python bot.py
```

## Connection to Control Panel

The bot reads these settings live from Supabase (changed via the dashboard):
- **Exchange rate** (`app_settings` table, key: `exchange_rate`)
- **Active wallets** (`wallets` table)
- **Blocked users** (`users.is_blocked`)

The bot writes to Supabase:
- **Deposit requests** → `transactions` table (status: pending)
- **Withdrawal requests** → `transactions` table (status: pending)
- **Incoming messages** → `bot_messages` table
- **User activity** → `users` table (upsert on every interaction)

The control panel dashboard shows all of this data in real time.

## Free Spin Button

The "اللفة المجانية" button now opens as a Telegram Mini Web App.
Update the URL in `utils/helpers.py` to point to your actual spin game page.
