from telegram.ext import ConversationHandler , MessageHandler , filters , CallbackQueryHandler , ContextTypes ,CommandHandler
from config.telegram import Update 
import store , config.telegram
MESSAGE = range(1)
async def button_admin_message_handler(update : Update , context:ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == 'admin_message':
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("ارسل رسالتك او ارسل صورة هنا") 
    return MESSAGE

async def get_message(update : Update , context:ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    telegram_id = update.message.from_user.id
    store.insertMessageToAdmin(telegram_id,message)
    await update.message.reply_text("تم إرسال الرسالة للأدمن") 
    try:
        await context.bot.send_message(chat_id=config.telegram.ADMIN_TELEGRAM_ID, text=message)
    except Exception as e:
        print(f"Error sending message to admin: {e}")
    return ConversationHandler.END

async def cancel(update : Update , context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('تم إلغاء عملية ارسال رسالة للأدمن')
    return ConversationHandler.END
def conversationHandler():
    
    conv_handeler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_admin_message_handler,pattern='^admin_message$')] ,
        states={
            MESSAGE :[MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )


    return conv_handeler
