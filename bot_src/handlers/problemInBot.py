from config.telegram import Update 
from telegram.ext import CallbackContext ,ContextTypes
async def handle_problem_in_bot(query):
    await query.message.reply_text("https://t.me/jadobotichancy")