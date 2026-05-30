from config.telegram import Update, ReplyKeyboardRemove
from services.iChancyAPI import iChancyAPI
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CommandHandler
)
import store

# 🔥 SUPABASE
import supabase_integration as supa
import handlers.ichancy
import Logger
logger = Logger.getLogger()

AMMOUNT = range(1)


async def button_deposit_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id

    # جلب بيانات الحساب من جدول users_ichancy_details في Supabase
    account = supa.get_ichancy_details_by_telegram_id(telegram_id)

    if not account or not account.get('username'):
        await update.callback_query.answer("❌ يجب إنشاء حساب iChancy أولاً", show_alert=True)
        return ConversationHandler.END

    player_id = account.get('player_id')
    username_ichancy = account.get('username')

    # جلب الرصيد من Supabase
    balance = supa.get_user_balance(telegram_id)

    # جلب رصيد iChancy من API
    api = handlers.ichancy.get_api()
    account_balance = 0
    if api and player_id:
        try:
            balance_result = api.get_player_balance_by_id(player_id)
            if balance_result.get('success'):
                account_balance = balance_result.get('balance', 0)
        except Exception as e:
            logger.warning(f"Could not fetch iChancy balance: {e}")

    context.user_data['player_id'] = player_id
    context.user_data['username_ichancy'] = username_ichancy
    context.user_data['balance'] = balance
    context.user_data['telegram_id'] = telegram_id

    await update.callback_query.edit_message_text(
        f"💰 **شحن رصيد حساب iChancy**\n\n"
        f"👤 الحساب: `{username_ichancy}`\n"
        f"💳 رصيدك في البوت: {balance:,.0f} ل.س\n\n"
        f"أدخل المبلغ المراد تحويله (بالليرة السورية):",
        parse_mode="Markdown"
    )
    return AMMOUNT


async def get_ammount_for_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ammountForDeposit = float(update.message.text.strip())
        if ammountForDeposit <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
            return AMMOUNT
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
        return AMMOUNT

    player_id = context.user_data.get('player_id')
    username_ichancy = context.user_data.get('username_ichancy')
    telegram_id = context.user_data.get('telegram_id')
    balance = context.user_data.get('balance', 0)

    # التحقق من الرصيد
    if balance < ammountForDeposit:
        await update.message.reply_text(
            f"❌ رصيدك غير كافي!\n\n"
            f"💳 رصيدك: {balance:,.0f} ل.س\n"
            f"💸 المطلوب: {ammountForDeposit:,.0f} ل.س"
        )
        return ConversationHandler.END

    # تنفيذ عملية الشحن عبر iChancy API
    api = handlers.ichancy.get_api()
    if not api:
        await update.message.reply_text("❌ لا يمكن الاتصال بخوادم iChancy حالياً")
        return ConversationHandler.END
    deposit_result = api.deposit_to_player(player_id, ammountForDeposit, "Telegram Bot Deposit")

    if deposit_result.get('success'):
        # خصم الرصيد من حساب المستخدم في البوت
        new_balance = balance - ammountForDeposit
        supa.update_user_balance(telegram_id, new_balance)

        # تسجيل العملية في Supabase
        try:
            supa.get_client().table("transactions_ichancy").insert({
                "telegram_id": str(telegram_id),
                "type": "deposit",
                "amount": ammountForDeposit,
                "new_balance": deposit_result.get('new_balance', 0),
                "status": "completed"
            }).execute()
        except Exception as e:
            logger.warning(f"Could not log ichancy transaction: {e}")

        # تسجيل في جدول المعاملات العام
        try:
            store.insertTransaction(
                telegram_id=telegram_id,
                value=ammountForDeposit,
                action_type="ichancy_deposit",
                provider_type="ichancy",
                transfer_num=username_ichancy or "-"
            )
        except Exception as e:
            logger.warning(f"Could not insert transaction: {e}")

        await update.message.reply_text(
            f"✅ **تم الشحن بنجاح!**\n\n"
            f"👤 الحساب: `{username_ichancy}`\n"
            f"💰 المبلغ: {ammountForDeposit:,.0f} ل.س\n"
            f"💳 رصيدك المتبقي: {new_balance:,.0f} ل.س",
            parse_mode="Markdown"
        )
        logger.info(f"ichancy deposit {ammountForDeposit} for user {telegram_id}")
    else:
        error_msg = deposit_result.get('error', 'Unknown error')
        await update.message.reply_text(f"❌ فشلت العملية: {error_msg}")
        logger.error(f"ichancy deposit failed for user {telegram_id}: {error_msg}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "تم إلغاء عملية الإيداع",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_deposit_account_handler, pattern="^deposit_account$")
        ],
        states={
            AMMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_ammount_for_deposit)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True,
        per_user=True,
        allow_reentry=True,
    )
    return conv_handler
