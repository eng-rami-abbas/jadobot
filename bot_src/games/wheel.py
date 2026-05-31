import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def wheel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text("🎡 يتم تدوير عجلة الحظ...")

    result = random.randint(0, 9)

    # تحديد الربح (مثال بسيط)
    if result == 0:
        msg = f"🎯 الرقم: {result}\n💀 خسرت! حاول مرة أخرى"
    elif result <= 3:
        msg = f"🎯 الرقم: {result}\n🙂 ربح بسيط!"
    elif result <= 7:
        msg = f"🎯 الرقم: {result}\n🔥 ربح متوسط!"
    else:
        msg = f"🎯 الرقم: {result}\n🎉 JACKPOT!"

    await update.message.reply_text(msg)