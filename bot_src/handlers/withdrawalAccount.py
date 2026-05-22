from telegram.ext import filters , CallbackContext , ConversationHandler ,MessageHandler , CallbackQueryHandler ,CommandHandler,ContextTypes
from config.telegram import ReplyKeyboardRemove, Update 
import store
from services.iChancyAPI import iChancyAPI
import handlers.ichancy
AMMOUNT = range(1)

async def button_withdrawal_from_account_handler(update:Update , context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    user = store.getUserByTelegramId(telegram_id)
    playerId = user.get('player_id')
    balance = user.get('balance')
    account_balance = user.get('account_balance')
    context.user_data['player_id'] = playerId
    context.user_data['balance'] = balance
    context.user_data['telegram_id'] = telegram_id
    context.user_data['account_balance'] = account_balance
    await update.callback_query.edit_message_text("ادخل المبلغ المراد سحبه")
    return AMMOUNT

async def get_withdraw_ammount(update:Update , context: ContextTypes.DEFAULT_TYPE):
    playerId= context.user_data.get('player_id')
    telegram_id = context.user_data.get('telegram_id')
    balance = context.user_data['balance']
    account_balance = context.user_data.get('account_balance')
    api = iChancyAPI()
    api.getPlayerBalanceById(playerId)
    ammount = int(update.message.text)
    if account_balance < ammount:
        await update.message.reply_text("عذرا ليس لديك الرصيد الكافي ")
        return ConversationHandler.END
    api.WirhdrawMoney(playerId ,ammount=ammount)
    user_id = store.getUserIdByTelegramId(telegram_id).get('id')
    store.insertInTransactionAccount(user_id , "done" , "withdraw" , value= -ammount)
    newBalance = balance + ammount*handlers.ichancy.EXCHANGE_RATE
    newAccountBalance = account_balance - ammount*handlers.ichancy.EXCHANGE_RATE
    store.update_user_account_balance(user_id , newAccountBalance)
    store.update_user_balance(user_id , newBalance)
    await update.message.reply_text('تم استلام المبلغ بنجاح')
    return ConversationHandler.END



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "تم إالغاء عملية الإيداع",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_withdrawal_from_account_handler , pattern='^withdrawal_account$')],
        states={
            AMMOUNT : [MessageHandler(filters.TEXT & ~filters.COMMAND , get_withdraw_ammount) ]
        },
        fallbacks=[CommandHandler('cancel' , cancel)]
    )
    return conv_handler