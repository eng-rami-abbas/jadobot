from services.iChancyAPI import iChancyAPI
import asyncio
import Logger, store
from config.telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler,
)
from services.transaction_notification_service import transaction_notification_service
import supabase_integration as supa

logger = Logger.getLogger()

transfer_num, value = range(2)

async def button_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'syriatel_cash_deposit':
        wallets = supa.get_active_wallets()
        syriatel_wallet = next((w for w in wallets if 'syriatel' in w.get('name', '').lower()), None)

        if syriatel_wallet:
            wallet_msg = syriatel_wallet.get('message_template') or syriatel_wallet.get('message') or ''
            wallet_num = syriatel_wallet.get('wallet_number') or syriatel_wallet.get('address') or '0991005298 / 0980375513'
            text = (
                f"ارسل الى احد الارقام التالية بطريقة التحويل اليدوي\n"
                f"{wallet_num}\n\n"
                f"{wallet_msg}\n"
                "ثم ادخل رقم عملية التحويل  👇\n"
            )
        else:
            text = (
                "ارسل الى احد الارقام التالية بطريقة التحويل اليدوي\n"
                "0991005298\n"
                "0980375513\n\n"
                "اقل قيمة للشحن هي 25,000\n"
                "وأي قيمة أقل من 25,000 لا يمكن شحنها او استرجاعها\n"
                "ثم ادخل رقم عملية التحويل  👇\n"
            )

        await query.edit_message_text(text=text)
        return transfer_num

    return ConversationHandler.END

async def get_transfer_num(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    telegram_user_id = str(update.effective_user.id)
    transfer_num_val = update.message.text
    context.user_data['transfer_num'] = transfer_num_val
    logger.info("User %s entered transfer number: %s", user.first_name, transfer_num_val)
    await update.message.reply_text(
        f"ادخل المبلغ الذي ارسلته بالليرة السورية"
    )
    return value

async def get_value(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    value_val = update.message.text
    context.user_data['value'] = value_val
    logger.info("User %s set value: %s", user.first_name, value_val)
    asyncio.create_task(handle_create_transaction(update, context=context))
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        'تم إلغاء عملية الشحن.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^syriatel_cash_deposit$')],
        states={
            transfer_num: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_transfer_num)],
            value: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_value)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True,
        per_user=True,
        allow_reentry=True,
    )
    return conv_handler

def getConfirmMarkup():
    keyboard = [
        [InlineKeyboardButton("تأكيد", callback_data='confirm_syriatel_cash_deposit')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    syriatelCashTransactionId = context.user_data.get('syriatelCashTransactionId')

    if syriatelCashTransactionId:
        await transaction_notification_service.notify_admin_new_transaction(syriatelCashTransactionId, 'syriatel')

    current_text = query.message.text
    success_text = current_text + "\n✅ تم إرسال طلبك للمراجعة. سيتم إشعارك عند الموافقة أو الرفض."

    await query.edit_message_text(
        text=success_text,
        reply_markup=None,
        parse_mode='Markdown'
    )

    return ConversationHandler.END

async def handle_create_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        telegram_user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name or telegram_user_id
        transfer_num_val = context.user_data.get('transfer_num')
        value_val = context.user_data.get('value')
        api = iChancyAPI()

        logger.info("API initialized successfully")

        syriatelCashTransactionId = store.insertTransaction(
            telegram_id=telegram_user_id,
            value=int(value_val),
            action_type='deposit',
            provider_type='syriatel',
            transfer_num=transfer_num_val
        )

        context.user_data['syriatelCashTransactionId'] = syriatelCashTransactionId

        try:
            supa.insert_deposit(
                telegram_id=int(telegram_user_id),
                username=username,
                amount_syp=float(value_val),
                transaction_id=transfer_num_val,
                wallet_name='Syriatel Cash'
            )
            logger.info("Deposit saved to Supabase dashboard")
        except Exception as e:
            logger.error(f"Supabase deposit save error: {e}")

        exchange_rate = supa.get_exchange_rate()
        amount_usd = float(value_val) / exchange_rate if exchange_rate > 0 else 0

        success_text = (
            "طلب شحن\n"
            "Syriatel Cash 🟢\n"
            "رقم العملية او العنوان: " + str(transfer_num_val) + "\n\n"
            "المبلغ بالليرة:  " + str(value_val) + " ل.س\n"
            f"ما يعادل: ${amount_usd:.2f}\n"
            "رقم الطلب: #" + str(syriatelCashTransactionId) + "\n\n"
        )

        await update.message.reply_text(success_text, reply_markup=getConfirmMarkup(), parse_mode='Markdown')

        try:
            import handlers.referral_system
            transaction_successful = True
            if transaction_successful and int(value_val) >= 25000:
                await handlers.referral_system.ReferralSystem.process_referral_earnings(
                    update, context, int(value_val), telegram_user_id
                )
        except ImportError:
            logger.warning("Referral system not available")
        except Exception as e:
            logger.error(f"Error processing referral earnings: {e}")

    except Exception as e:
        logger.error(f"Error in handle_create_transaction: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء الطلب. يرجى المحاولة مرة أخرى.")

    finally:
        context.user_data.pop('transfer_num', None)
        context.user_data.pop('value', None)
