"""
نظام رد الإدمن الآلي
"""

import re
import logging
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class AdminAutoReply:
    """نظام الرد الآلي للإدمن"""
    
    KEYWORDS_RESPONSES = {
        # كلمات متعلقة بالإيداع
        r"(ايداع|شحن|تحويل|دفع|فلوس|مبلغ)": "💰 مشاكل الإيداع: تحقق من رقم العملية والمبلغ",
        r"(سحب|سحب رصيد|تحويل لي)": "💸 مشاكل السحب: تأكد من كفاية الرصيد وصحة البيانات",
        r"(حساب|تسجيل دخول|كلمة سر)": "👤 مشاكل الحساب: https://www.ichancy.com/ar",
        r"(هدية|كود|هدايا)": "🎁 مشاكل الهدايا: تأكد من صحة الكود وصلاحيته",
        r"(موقع|رابط|انترنت)": "🌐 رابط الموقع: https://www.ichancy.com",
        r"(متى|مدة|وقت|انتظار)": "⏰ وقت المعالجة: 24 ساعة كحد أقصى",
    }
    
    @staticmethod
    async def auto_reply_to_user(user_id: int, message: str, context: ContextTypes.DEFAULT_TYPE):
        """الرد الآلي على رسالة المستخدم"""
        try:
            # البحث عن كلمات مفتاحية
            response = None
            for pattern, reply in AdminAutoReply.KEYWORDS_RESPONSES.items():
                if re.search(pattern, message, re.IGNORECASE):
                    response = reply
                    break
            
            if response:
                # إرسال الرد الآلي
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🤖 **رد آلي:**\n\n{response}\n\n📞 للمزيد: @{context.bot.username}",
                    parse_mode='Markdown'
                )
                return True
                
        except Exception as e:
            logger.error(f"Error in auto reply: {e}")
        
        return False