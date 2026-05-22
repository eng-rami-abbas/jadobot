import Logger
from config.telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils import helpers
logger = Logger.getLogger()

async def handle_back_to_menu(query , username):
    """Return to main menu"""
    
    reply_markup = helpers.getReplyMarkup()
    text_welcome = helpers.getTextWelcome(username)
    await query.edit_message_text(
        text_welcome,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )