import store
from config.telegram import Update
from telegram.ext import ContextTypes
import supabase_integration as supa

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Balance command handler - جلب الرصيد من Supabase"""
    user_id = update.effective_user.id

    try:
        # جلب الرصيد من Supabase
        balance_syp = supa.get_user_balance(user_id)

        # تنسيق الرصيد مع فواصل الآلاف
        formatted_balance = f"{balance_syp:,.0f}"

        await update.message.reply_text(
            f"💳 رصيدك الحالي:\n\n"
            f"{formatted_balance} ل.س\n\n"
            f"🆔 معرف التلغرام: {user_id}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في جلب الرصيد: {e}")
