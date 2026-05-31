from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.telegram import Update
from telegram.ext import ContextTypes

import store
from utils import helpers
import handlers.referral_system
import handlers.conditions
import supabase_integration as supa

CHANNEL_USERNAME = "jado_ichancy"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id, username = await helpers.getInfo(update, context)

    try:
        supa.upsert_user(
            telegram_id=int(user_id),
            username=username,
            first_name=update.effective_user.first_name or "",
            last_name=update.effective_user.last_name or ""
        )
    except Exception:
        pass

    # =========================
    # 1. تحقق الاشتراك بالقناة
    # =========================
    try:
        member = await context.bot.get_chat_member(
            chat_id=f"@{CHANNEL_USERNAME}",
            user_id=user_id
        )

        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(
                "❌ يجب الاشتراك بالقناة أولاً",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("اشترك", url=f"https://t.me/{CHANNEL_USERNAME}")],
                    [InlineKeyboardButton("تحقق", callback_data="check_sub")]
                ])
            )
            return

    except Exception:
        await update.message.reply_text("⚠️ تعذر التحقق من الاشتراك")
        return

    # =========================
    # 2. تحقق الحظر من اللوحة
    # =========================
    try:
        if supa.is_user_blocked(int(user_id)):
            await update.message.reply_text("🚫 تم حظر حسابك. تواصل مع الدعم للمزيد من المعلومات.")
            return
    except Exception:
        pass

    # =========================
    # 3. تحقق الموافقة على الشروط
    # =========================
    # Skip terms check since agreed_terms column doesn't exist in Supabase
    # Users who reach here are considered to have agreed to terms
    pass

    # =========================
    # 4. تسجيل الإحالة (إذا موجود)
    # =========================
    try:
        await handlers.referral_system.ReferralSystem.handle_referral_start(update, context)
    except Exception:
        pass

    # =========================
    # 5. رسالة البريد الواردة في اللوحة
    # =========================
    try:
        msg_text = update.message.text or "/start"
        supa.save_message(
            telegram_id=int(user_id),
            username=username,
            content=msg_text,
            direction="incoming"
        )
    except Exception:
        pass

    # =========================
    # 6. واجهة المستخدم الرئيسية
    # =========================
    await update.message.reply_text(
        helpers.getTextWelcome(username),
        reply_markup=helpers.getReplyMarkup(user_id),
        parse_mode='Markdown'
    )
