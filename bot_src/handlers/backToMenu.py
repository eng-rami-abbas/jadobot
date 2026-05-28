import Logger
from config.telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils import helpers
logger = Logger.getLogger()

async def handle_back_to_menu(query, username):
    """Return to main menu"""

    reply_markup = helpers.getReplyMarkup()
    text_welcome = helpers.getTextWelcome(username)

    try:
        # First try to edit the message
        await query.edit_message_text(
            text_welcome,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in edit_message_text: {e}")
        try:
            # If edit fails, try to delete and send new message
            await query.message.delete()
            await query.message.chat.send_message(
                text=text_welcome,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e2:
            logger.error(f"Error in send_message fallback: {e2}")
            # Final fallback - just send a new message
            await query.message.reply_text(
                text_welcome,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
