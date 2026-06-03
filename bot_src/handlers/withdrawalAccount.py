from telegram.ext import filters, CallbackContext, ConversationHandler, MessageHandler, CallbackQueryHandler, CommandHandler, ContextTypes
from config.telegram import ReplyKeyboardRemove, Update
from services.iChancyAPI import iChancyAPI
import store

# SUPABASE
import supabase_integration as supa
import handlers.ichancy
import Logger
logger = Logger.getLogger()

AMMOUNT = range(1)


async def button_withdrawal_from_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id

    # جلب بيانات الحساب من جدول users_ichancy_details في Supabase
    account = supa.get_ichancy_details_by_telegram_id(telegram_id)

    if not account or not account.get('username'):
        await update.callback_query.answer("❌ يجب إنشاء حساب iChancy أولاً", show_alert=True)
        return ConversationHandler.END

    player_id = account.get('player_id')
    username_ichancy = account.get('username')

    # جلب الرصيد من iChancy API
    api = handlers.ichancy.get_api()
    account_balance = 0
    if api and player_id:
        try:
            balance_result = await api.get_player_balance_by_id(player_id)
            if balance_result.get('success'):
                account_balance = balance_result.get('balance', 0)
        except Exception as e:
            logger.warning(f"Could not fetch iChancy balance: {e}")

    # جلب رصيد البوت
    bot_balance = supa.get_user_balance(telegram_id)

    context.user_data['player_id'] = player_id
    context.user_data['username_ichancy'] = username_ichancy
    context.user_data['telegram_id'] = telegram_id
    context.user_data['account_balance'] = account_balance
    context.user_data['bot_balance'] = bot_balance

    await update.callback_query.edit_message_text(
        f"💸 **سحب رصيد من حساب iChancy**\n\n"
        f"👤 الحساب: `{username_ichancy}`\n"
        f"💰 رصيدك في iChancy: {account_balance:,.2f}\n"
        f"💳 رصيدك في البوت: {bot_balance:,.0f} ل.س\n\n"
        f"أدخل المبلغ المراد سحبه من iChancy:",
        parse_mode="Markdown"
    )
    return AMMOUNT


async def get_withdraw_ammount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ammount = float(update.message.text.strip())
        if ammount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
            return AMMOUNT
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
        return AMMOUNT

    player_id = context.user_data.get('player_id')
    username_ichancy = context.user_data.get('username_ichancy')
    telegram_id = context.user_data.get('telegram_id')
    account_balance = context.user_data.get('account_balance', 0)
    bot_balance = context.user_data.get('bot_balance', 0)

    # التحقق من الرصيد في iChancy
    if account_balance < ammount:
        await update.message.reply_text(
            f"❌ رصيدك في iChancy غير كافي!\n\n"
            f"💰 رصيدك: {account_balance:,.2f}\n"
            f"💸 المطلوب: {ammount:,.2f}"
        )
        return ConversationHandler.END

    # تنفيذ عملية السحب عبر iChancy API
    api = handlers.ichancy.get_api()
    if not api:
        await update.message.reply_text("❌ لا يمكن الاتصال بخوادم iChancy حالياً")
        return ConversationHandler.END

    withdraw_result = await api.withdraw_from_player(player_id, ammount, "Telegram Bot Withdrawal")

    if withdraw_result.get('success'):
        # OPTIMIZED: Update balance and log transactions
        try:
            # إضافة الرصيد إلى حساب المستخدم في البوت
            new_bot_balance = bot_balance + ammount
            supa.update_user_balance(telegram_id, new_bot_balance)

            # Fire and forget for non-critical logs
            asyncio.create_task(_log_withdrawal_async(
                telegram_id, ammount, withdraw_result.get('new_balance', 0), username_ichancy
            ))

            await update.message.reply_text(
                f"✅ **تم السحب بنجاح!**\n\n"
                f"👤 الحساب: `{username_ichancy}`\n"
                f"💸 المبلغ المسحوب: {ammount:,.2f}\n"
                f"💳 رصيدك في البوت: {new_bot_balance:,.0f} ل.س",
                parse_mode="Markdown"
            )
            logger.info(f"ichancy withdrawal {ammount} for user {telegram_id}")
        except Exception as e:
            logger.error(f"Error updating balance after withdrawal: {e}")
            await update.message.reply_text(
                f"✅ **تم السحب بنجاح!**\n\n"
                f"👤 الحساب: `{username_ichancy}`\n"
                f"💸 المبلغ المسحوب: {ammount:,.2f}\n\n"
                f"⚠️ تم السحب من الموقع لكن حدث خطأ في تحديث رصيد البوت. تواصل مع الدعم.",
                parse_mode="Markdown"
            )
    else:
        error_msg = withdraw_result.get('error', 'Unknown error')
        await update.message.reply_text(f"❌ فشلت العملية: {error_msg}")
        logger.error(f"ichancy withdrawal failed for user {telegram_id}: {error_msg}")

    return ConversationHandler.END


async def _log_withdrawal_async(telegram_id, amount, new_balance, username_ichancy):
    """Fire-and-forget logging to avoid blocking the response."""
    try:
        # تسجيل العملية في Supabase
        try:
            supa.get_client().table("transactions_ichancy").insert({
                "telegram_id": str(telegram_id),
                "type": "withdraw",
                "amount": amount,
                "new_balance": new_balance,
                "status": "completed"
            }).execute()
        except Exception as e:
            logger.warning(f"Could not log ichancy transaction: {e}")

        # تسجيل في جدول المعاملات العام
        try:
            store.insertTransaction(
                telegram_id=telegram_id,
                value=amount,
                action_type="ichancy_withdrawal",
                provider_type="ichancy",
                transfer_num=username_ichancy or "-"
            )
        except Exception as e:
            logger.warning(f"Could not insert transaction: {e}")
    except Exception as e:
        logger.warning(f"Async withdrawal logging error: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "تم إلغاء عملية السحب",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_withdrawal_from_account_handler, pattern='^withdrawal_account$')],
        states={
            AMMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_withdraw_ammount)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )
    return conv_handler
