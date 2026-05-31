import os
import json
from urllib.parse import urlencode
from telegram import InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
import Logger
import supabase_integration as supa
from dotenv import load_dotenv

load_dotenv()

logger = Logger.getLogger()

WHEEL_WEBAPP_URL = os.getenv(
    'WHEEL_WEBAPP_URL',
    'https://eng-rami-abbas.github.io/jadobot/',
).rstrip('/')


def get_wheel_webapp_url(telegram_id: str) -> str:
    base = WHEEL_WEBAPP_URL
    if not base.endswith('.html'):
        base = f"{base}/index.html" if not base.endswith('/') else f"{base}index.html"
    sep = '&' if '?' in base else '?'
    return f"{base}{sep}{urlencode({'user_id': telegram_id})}"


def get_wheel_button(telegram_id: str) -> InlineKeyboardButton:
    """إرجاع زر WebApp جاهز للاستخدام في القائمة الرئيسية."""
    url = get_wheel_webapp_url(telegram_id)
    return InlineKeyboardButton("🎰 لفة مجانية", web_app=WebAppInfo(url=url))


async def handle_web_app_data(update, context):
    """استقبال نتيجة التدوير من WebApp."""
    if not update.message or not update.message.web_app_data:
        return

    try:
        data = json.loads(update.message.web_app_data.data)
        prize = data.get('prize', {}) or {}
        user_id = str(update.effective_user.id)
        logger.info(f"Web App data received: {data}")

        prize_type = prize.get('type')
        label = prize.get('label_ar') or prize.get('label') or ''
        amount = int(prize.get('amount') or 0)
        percent = float(prize.get('percent') or 0)

        if prize_type == 'cash' and amount:
            bal = supa.get_user_balance(user_id)
            await update.message.reply_text(
                f"🎉 مبروك!\nلقد ربحت {amount:,} ل.س\n💳 رصيدك: {bal / 100:,.0f} ل.س"
            )
        elif prize_type == 'bonus':
            await update.message.reply_text(
                f"🎉 مبروك!\nبونص {percent:g}% على أول إيداع قادم (مرة واحدة)."
            )
        elif prize_type == 'premium':
            await update.message.reply_text(
                f"🎁 مبروك!\nفزت بـ Telegram Premium.\nسيتواصل معك الدعم قريباً."
            )
        elif prize_type == 'respin':
            await update.message.reply_text(
                "🔄 مبروك!\nحصلت على إعادة تدوير — اضغط «اللفة المجانية» ولفّ مرة أخرى."
            )
        else:
            await update.message.reply_text(
                f"😔 حظ أوفر!\n{label or 'حاول مرة أخرى غداً بعد إيداع.'}"
            )

    except json.JSONDecodeError:
        logger.error("Invalid JSON from Web App")
        await update.message.reply_text("❌ حدث خطأ في معالجة النتيجة")
    except Exception as e:
        logger.error(f"Error handling web app data: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع")
