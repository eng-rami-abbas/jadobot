# handlers/contact_handler.py (نظام مبسط)
import logging
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class ContactHandler:
    @staticmethod
    async def contact_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """قائمة الاتصال الرئيسية"""
        keyboard = [
            [InlineKeyboardButton("📧 رسالة للإدمن", callback_data='message_admin')],
            [InlineKeyboardButton("📞 معلومات الدعم", callback_data='support_info')],
            [InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data='faq')],
            [InlineKeyboardButton("📌 الشروط والأحكام", callback_data='terms')],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """
📧 **نظام الاتصال**

اختر طريقة الاتصال المناسبة:
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)