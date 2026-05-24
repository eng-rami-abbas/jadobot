import os
import json
from urllib.parse import urlencode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
import Logger
import supabase_integration as supa
from dotenv import load_dotenv

load_dotenv()

logger = Logger.getLogger()

# إعدادات العجلة
WHEEL_WEBAPP_URL = os.getenv(
    'WHEEL_WEBAPP_URL',
    'https://yourusername.github.io/jadoo-bot-latest/wheel_project/wheel.html',
).rstrip('/')


def get_wheel_webapp_url(telegram_id: str) -> str:
    base = WHEEL_WEBAPP_URL if WHEEL_WEBAPP_URL.endswith('.html') else f"{WHEEL_WEBAPP_URL}/wheel.html"
    sep = '&' if '?' in base else '?'
    return f"{base}{sep}{urlencode({'user_id': telegram_id})}"

async def handle_spin_wheel(update, context):
    """فتح واجهة العجلة المجانية بعد شحن اليوم."""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)

    try:
        last_spin = supa.get_wheel_last_spin(user_id)
        if last_spin:
            from datetime import datetime, timezone
            import pytz
            damascus = pytz.timezone("Asia/Damascus")
            last_spin_time = datetime.fromisoformat(last_spin.replace("Z", "+00:00"))
            if last_spin_time.tzinfo is None:
                last_spin_time = last_spin_time.replace(tzinfo=timezone.utc)
            last_local = last_spin_time.astimezone(damascus)
            now_local = datetime.now(damascus)
            if last_local.date() == now_local.date():
                await query.edit_message_text(
                    "⏰ لقد استخدمت اللفة المجانية اليوم. تعود اللفة بعد شحن يوم جديد.",
                    reply_markup=get_wheel_keyboard()
                )
                return
    except Exception as e:
        logger.error(f"Error checking wheel cooldown: {e}")

    try:
        if not supa.has_deposited_today(user_id):
            await query.edit_message_text(
                "🔒 اللفة المجانية متاحة فقط بعد شحن اليوم نفسه. قم بعمل إيداع واحد اليوم لتحصل على لفة مجانية.",
                reply_markup=get_wheel_keyboard()
            )
            return
    except Exception as e:
        logger.error(f"Error checking daily deposit eligibility: {e}")
        await query.edit_message_text(
            "⚠️ حدث خطأ أثناء التحقق من صلاحية اللفة. حاول مرة أخرى لاحقاً.",
            reply_markup=get_wheel_keyboard()
        )
        return

    wheel_url = get_wheel_webapp_url(user_id)
    keyboard = [
        [InlineKeyboardButton("🎰 اضغط هنا للدوران", web_app=WebAppInfo(url=wheel_url))],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            "🎰 **اللفة المجانية**\n\nاضغط على الزر أدناه لفتح العجلة!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception:
        await query.message.reply_text(
            "🎰 **اللفة المجانية**\n\nاضغط على الزر أدناه لفتح العجلة!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

def get_wheel_keyboard():
    """لوحة مفاتيح العجلة"""
    keyboard = [
        [InlineKeyboardButton("🎰 لفة مجانية", callback_data="spin_wheel")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_web_app_data(update, context):
    """معالجة البيانات المرسلة من Web App"""
    if not update.message or not update.message.web_app_data:
        return

    try:
        data = json.loads(update.message.web_app_data.data)
        prize = data.get('prize', {})
        user_id = str(update.effective_user.id)

        # Prevent double spin same day
        last_spin = supa.get_wheel_last_spin(user_id)
        if last_spin:
            from datetime import datetime, timezone
            import pytz
            damascus = pytz.timezone("Asia/Damascus")
            last_spin_time = datetime.fromisoformat(last_spin.replace("Z", "+00:00"))
            if last_spin_time.tzinfo is None:
                last_spin_time = last_spin_time.replace(tzinfo=timezone.utc)
            if last_spin_time.astimezone(damascus).date() == datetime.now(damascus).date():
                await update.message.reply_text("⏰ لقد استخدمت لفة اليوم مسبقاً.")
                return

        logger.info(f"Web App data received: {data}")

        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)

        prize_type = prize.get('type') if isinstance(prize, dict) else None

        label = prize.get('label') or prize.get('cad_text') or ''

        if prize_type == 'cash':
            display_amount = int(prize.get('amount', 0))
            credit_amount = display_amount * 100  # same units as deposit (amount_syp stored x100)
            current_balance = supa.get_user_balance(user_id)
            new_balance = int(current_balance + credit_amount)
            supa.update_user_balance(user_id, new_balance)
            supa.set_wheel_last_spin(user_id, now_utc.isoformat())

            await update.message.reply_text(
                f"🎉 تهانينا! ربحت {display_amount:,.0f} ل.س وتم إضافته إلى رصيدك.\n"
                f"💳 رصيدك الآن: {new_balance / 100:,.0f} ل.س"
            )

        elif prize_type == 'bonus':
            bonus_percent = float(prize.get('percent', 0) or 0)
            supa.set_wheel_last_spin(user_id, now_utc.isoformat(), pending_bonus_percent=bonus_percent)

            await update.message.reply_text(
                f"🎉 مبروك! ربحت بونص {bonus_percent:g}% على أول إيداع بعد هذه اللفة.\n"
                f"سيُضاف البونص تلقائياً عند موافقة الإدارة على إيداعك القادم (مرة واحدة فقط)."
            )

        elif prize_type == 'gift':
            supa.set_wheel_last_spin(user_id, now_utc.isoformat())
            await update.message.reply_text(
                f"🎁 مبروك! {label or 'حصلت على هدية من العجلة'}.\nتواصل مع الدعم لاستلامها."
            )

        elif prize_type == 'respin':
            await update.message.reply_text(
                "🔄 حظ أوفر في هذه اللفة — يمكنك المحاولة غداً بعد إيداع جديد."
            )
            supa.set_wheel_last_spin(user_id, now_utc.isoformat())

        else:
            supa.set_wheel_last_spin(user_id, now_utc.isoformat())
            await update.message.reply_text(
                f"😢 حظ أوفر! {label or 'لم تحصل على جائزة هذه المرة.'}\nتعود اللفة المجانية غداً بعد إيداع."
            )

    except json.JSONDecodeError:
        logger.error("Invalid JSON from Web App")
        await update.message.reply_text("❌ حدث خطأ في معالجة النتيجة")
    except Exception as e:
        logger.error(f"Error handling web app data: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع")
