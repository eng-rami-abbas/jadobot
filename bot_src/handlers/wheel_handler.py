import os
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
import Logger
import supabase_integration as supa
from dotenv import load_dotenv

load_dotenv()

logger = Logger.getLogger()

# إعدادات العجلة
WHEEL_WEBAPP_URL = os.getenv('WHEEL_WEBAPP_URL', 'https://yourusername.github.io/jadoo-bot-latest/wheel_project/')

async def handle_spin_wheel(update, context):
    """فتح واجهة العجلة المجانية بعد شحن اليوم."""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)

    try:
        last_spin = supa.get_wheel_last_spin(user_id)
        if last_spin:
            from datetime import datetime, timezone
            last_spin_time = datetime.fromisoformat(last_spin)
            if last_spin_time.tzinfo is None:
                last_spin_time = last_spin_time.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)
            if last_spin_time.date() == now_utc.date():
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

    keyboard = [
        [InlineKeyboardButton("🎰 اضغط هنا للدوران", web_app=WebAppInfo(url=WHEEL_WEBAPP_URL))],
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

        logger.info(f"Web App data received: {data}")

        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)

        prize_type = prize.get('type') if isinstance(prize, dict) else None

        if prize_type == 'cash':
            amount = int(prize.get('amount', 0))
            current_balance = supa.get_user_balance(user_id)
            new_balance = int(current_balance + amount)
            supa.update_user_balance(user_id, new_balance)
            supa.set_wheel_last_spin(user_id, now_utc.isoformat())

            await update.message.reply_text(
                f"🎉 تهانينا! ربحت {amount:,.0f} ل.س وتم إضافته إلى رصيدك.\nالرصيد الآن: {new_balance:,.0f} ل.س"
            )

        elif prize_type == 'bonus':
            bonus_percent = float(prize.get('percent', 0) or 0)
            supa.set_wheel_last_spin(user_id, now_utc.isoformat(), pending_bonus_percent=bonus_percent)

            await update.message.reply_text(
                f"🎉 مبروك! ربحـت {bonus_percent:.0f}% بونص للشحن القادم. سيتم تفعيله مرة واحدة على أول إيداع بعد هذه اللفة."
            )

        else:
            supa.set_wheel_last_spin(user_id, now_utc.isoformat())
            await update.message.reply_text(
                "😢 حظ أوفر! لم تحصل على جائزة هذه المرة. حاول غداً."
            )

    except json.JSONDecodeError:
        logger.error("Invalid JSON from Web App")
        await update.message.reply_text("❌ حدث خطأ في معالجة النتيجة")
    except Exception as e:
        logger.error(f"Error handling web app data: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع")
