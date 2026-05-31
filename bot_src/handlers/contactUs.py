from config.telegram import InlineKeyboardButton , InlineKeyboardMarkup

async def handle_contact_us(query):
    text = "الدعم"
    keyboard = [[InlineKeyboardButton('مشكلة تقنية ضمن البوت' , callback_data = "problem_in_bot")],
                [InlineKeyboardButton('مشكلة تقنية ضمن الموقع' , callback_data = "problem_in_website")],
                [InlineKeyboardButton('القائمة الرئيسية', callback_data = "back_to_menu")]
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text , reply_markup = reply_markup )