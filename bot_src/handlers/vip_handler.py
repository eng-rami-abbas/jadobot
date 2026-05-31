# handlers/vip_handler.py
import logging
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class VIPHandler:
    @staticmethod
    async def vip_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معلومات نظام VIP"""
        keyboard = [
            [InlineKeyboardButton("📊 مستواي الحالي", callback_data='my_vip_level')],
            [InlineKeyboardButton("🎁 مزايا VIP", callback_data='vip_benefits')],
            [InlineKeyboardButton("📈 كيفية الترقية", callback_data='vip_upgrade')],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """
👑 **برنامج الولاء VIP**

🎯 **المستويات:**
🆕 **مبتدئ:** 0-10,000 ليرة رهانات
🥉 **برونز:** 10,000-50,000 ليرة
🥈 **فضة:** 50,000-200,000 ليرة
🥇 **ذهب:** 200,000-1,000,000 ليرة
💎 **الماس:** أكثر من 1,000,000 ليرة

💰 **المزايا:**
• نسبة كاش باك أعلى
• دعم فني متميز
• مكافآت شهرية
• دعوات لأحداث خاصة

📈 **كيفية الترقية:**
ارفع من قيمة رهاناتك لترتقي في المستويات!
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)