from config.telegram import  InlineKeyboardButton, InlineKeyboardMarkup

async def handle_help(query):
    """Show help information"""
    keyboard = [[InlineKeyboardButton("🏠 Back to Menu", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("help", reply_markup=reply_markup, parse_mode='Markdown')