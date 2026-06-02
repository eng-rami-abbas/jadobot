"""
نظام الدعم الفني والرد الآلي المتكامل
"""

import logging
import json
import re
from datetime import datetime, timedelta
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError

import store
import config.telegram
from utils import helpers

logger = logging.getLogger(__name__)

# حالات المحادثة
SUPPORT_CATEGORY, SUPPORT_MESSAGE, SUPPORT_CONFIRM = range(3)

class SupportSystem:
    """نظام الدعم الفني والرد الآلي"""
    
    # قوالب الردود الآلية
    AUTO_RESPONSES = {
        "deposit": {
            "question": "مشكلة في الإيداع",
            "response": """💰 **مشاكل الإيداع الشائعة:**

✅ **الحلول المقترحة:**
1. تأكد من إدخال رقم العملية الصحيح
2. الحد الأدنى للإيداع: 25,000 ليرة
3. وقت المعالجة: 24 ساعة كحد أقصى
4. تأكد من صحة رقم السيرياتيل

📞 **إذا استمرت المشكلة:**
• تواصل مع الإدمن مباشرة
• أرسل رقم العملية والمبلغ
• انتظر الرد خلال ساعات العمل

⏰ **ساعات الدعم:**
• 24/7 للإشعارات
• 9 صباحاً - 12 منتصف الليل للردود"""
        },
        "withdrawal": {
            "question": "مشكلة في السحب",
            "response": """💸 **مشاكل السحب الشائعة:**

✅ **الحلول المقترحة:**
1. تأكد من كفاية الرصيد
2. الحد الأدنى للسحب: 10,000 ليرة
3. وقت المعالجة: 24 ساعة كحد أقصى
4. تأكد من صحة بيانات التحويل

📞 **إذا استمرت المشكلة:**
• تأكد من صحة الرصيد
• تحقق من حالة الطلب
• تواصل مع الإدمن إذا تجاوزت 24 ساعة"""
        },
        "account": {
            "question": "مشكلة في الحساب",
            "response": """👤 **مشاكل الحساب الشائعة:**

✅ **الحلول المقترحة:**
1. تأكد من بيانات تسجيل الدخول
2. رابط الموقع: https://www.ichancy.com/ar
3. يمكنك استعادة كلمة المرور من الموقع
4. للإشعارات المهمة، تأكد من تفعيلها

🔗 **للمساعدة الفورية:**
• تواصل مع دعم الموقع الرسمي
• استخدم البريد الإلكتروني
• الدردشة المباشرة على الموقع"""
        },
        "gift": {
            "question": "مشكلة في الهدايا",
            "response": """🎁 **مشاكل الهدايا الشائعة:**

✅ **الحلول المقترحة:**
1. تأكد من صحة كود الهدية
2. تحقق من صلاحية الكود
3. تأكد من كفاية رصيد المرسل
4. الحد الأدنى للهدية: 1,000 ليرة

🎯 **ملاحظات مهمة:**
• كود الهدية صالح لاستخدام واحد
• يجب إدخال الكود كما هو
• الإهداء متاح بين جميع المستخدمين"""
        },
        "other": {
            "question": "مشكلة أخرى",
            "response": """❓ **مشاكل أخرى:**

📞 **طرق التواصل:**
• الإدمن: @{}
• الموقع: https://www.ichancy.com
• البريد: support@ichancy.com

⏰ **وقت الرد المتوقع:**
• خلال 24 ساعة للإشعارات
• خلال 12 ساعة للرسائل العاجلة
• خلال 6 ساعات للمشاكل الحرجة

🎯 **للمساعدة السريعة:**
1. وصف المشكلة بدقة
2. أرفق الصور إذا لزم الأمر
3. اذكر رقم المستخدم أو المعاملة"""
        }
    }
    
    # الأسئلة الشائعة
    FAQ = {
        "deposit_time": {
            "question": "⏰ كم يستغرق وقت الإيداع؟",
            "answer": "⏳ وقت معالجة الإيداع: 24 ساعة كحد أقصى\n✅ عادةً يتم خلال 2-6 ساعات"
        },
        "withdrawal_time": {
            "question": "⏰ كم يستغرق وقت السحب؟",
            "answer": "⏳ وقت معالجة السحب: 24 ساعة كحد أقصى\n✅ يتم التحويل خلال 12 ساعة عادةً"
        },
        "min_deposit": {
            "question": "💰 ما هو الحد الأدنى للإيداع؟",
            "answer": "💵 الحد الأدنى للإيداع:\n• سيرياتيل كاش: 25,000 ليرة\n• البنك: 10,000 ليرة\n• USDT: 10,000 ليرة"
        },
        "min_withdrawal": {
            "question": "💰 ما هو الحد الأدنى للسحب؟",
            "answer": "💸 الحد الأدنى للسحب:\n• جميع الطرق: 10,000 ليرة\n• الحد الأقصى: 5,000,000 ليرة"
        },
        "gift_min": {
            "question": "🎁 ما هو الحد الأدنى للإهداء؟",
            "answer": "🎁 الحد الأدنى للإهداء: 1,000 ليرة\n💰 الحد الأقصى: حسب رصيدك"
        },
        "referral_percentage": {
            "question": "👥 ما هي نسبة الإحالة؟",
            "answer": "💰 نسبة الإحالة: 10%\n🎁 مكافآت إضافية عند:\n• 5 إحالات: 5,000 ليرة\n• 10 إحالات: 15,000 ليرة"
        },
        "website": {
            "question": "🌐 ما هو رابط الموقع؟",
            "answer": "🔗 رابط الموقع الرسمي:\nhttps://www.ichancy.com/ar\n📱 رابط الدعم المباشر:\nhttps://www.ichancy.com/ar/contact-us"
        },
        "support": {
            "question": "📞 كيف أتواصل مع الدعم؟",
            "answer": "📞 طرق التواصل:\n• https://t.me/jado_ichancy (تليجرام)\n• support@ichancy.com (بريد)\n• https://www.ichancy.com/support (موقع)"
        }
    }
    
    @staticmethod
    async def contact_us_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """قائمة تواصل معنا"""
        query = update.callback_query
        await query.answer()
        
        message = """
✉️ **تواصل معنا**

📞 **طرق التواصل المتاحة:**

1️⃣ **الدعم الفني للبوت:**
• @{}
• مشاكل تقنية في البوت فقط

2️⃣ **الدعم الفني للموقع:**
• https://www.ichancy.com/ar/contact-us
• مشاكل في الموقع أو الحسابات

3️⃣ **البريد الإلكتروني:**
• support@ichancy.com
• للاستفسارات الرسمية

4️⃣ **صفحة الفيسبوك:**
• https://www.facebook.com/ichancy.co
• آخر الأخبار والعروض

🎯 **للمساعدة السريعة:**
• اختر نوع المشكلة
• اتبع التعليمات
• احصل على المساعدة المناسبة
        """.format(config.telegram.ADMIN_TELEGRAM_ID)
        
        keyboard = [
            [
                InlineKeyboardButton("📱 مشكلة تقنية في البوت", callback_data='problem_in_bot'),
                InlineKeyboardButton("🌐 مشكلة تقنية في الموقع", callback_data='problem_in_website')
            ],
            [
                InlineKeyboardButton("❓ أسئلة شائعة", callback_data='faq_menu'),
                InlineKeyboardButton("📨 رسالة للإدمن", callback_data='admin_message')
            ],
            [
                InlineKeyboardButton("🔧 طلب دعم فني", callback_data='tech_support'),
                InlineKeyboardButton("📞 تواصل مباشر", callback_data='direct_contact')
            ],
            [
                InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def faq_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """قائمة الأسئلة الشائعة"""
        query = update.callback_query
        await query.answer()
        
        keyboard = []
        row = []
        
        # إضافة الأسئلة الشائعة
        for i, (key, faq) in enumerate(SupportSystem.FAQ.items()):
            row.append(InlineKeyboardButton(faq["question"], callback_data=f'faq_{key}'))
            
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='contact_us')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❓ **الأسئلة الشائعة**\n\nاختر سؤالاً للحصول على الإجابة:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def show_faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إجابة السؤال الشائع"""
        query = update.callback_query
        await query.answer()
        
        faq_key = query.data.replace('faq_', '')
        faq = SupportSystem.FAQ.get(faq_key)
        
        if faq:
            message = f"""
{faq['question']}

{faq['answer']}

🔙 العودة لقائمة الأسئلة الشائعة
            """
        else:
            message = "❌ السؤال غير موجود"
        
        keyboard = [
            [InlineKeyboardButton("🔙 الأسئلة الشائعة", callback_data='faq_menu')],
            [InlineKeyboardButton("✉️ تواصل معنا", callback_data='contact_us')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def tech_support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء طلب الدعم الفني"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['support_type'] = 'technical'
        
        keyboard = [
            [
                InlineKeyboardButton("💰 مشكلة في الإيداع", callback_data='support_deposit'),
                InlineKeyboardButton("💸 مشكلة في السحب", callback_data='support_withdrawal')
            ],
            [
                InlineKeyboardButton("👤 مشكلة في الحساب", callback_data='support_account'),
                InlineKeyboardButton("🎁 مشكلة في الهدايا", callback_data='support_gift')
            ],
            [
                InlineKeyboardButton("❓ مشكلة أخرى", callback_data='support_other'),
                InlineKeyboardButton("🔙 رجوع", callback_data='contact_us')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 **طلب دعم فني**\n\nاختر نوع المشكلة:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def handle_support_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة فئة الدعم"""
        query = update.callback_query
        await query.answer()
        
        category = query.data.replace('support_', '')
        context.user_data['support_category'] = category
        
        if category in SupportSystem.AUTO_RESPONSES:
            # عرض الرد الآلي أولاً
            response = SupportSystem.AUTO_RESPONSES[category]['response']
            
            if category == 'other':
                response = response.format(config.telegram.ADMIN_TELEGRAM_ID)
            
            message = f"""
🔧 **{SupportSystem.AUTO_RESPONSES[category]['question']}**

{response}

📝 **إذا لم تجد حلاً:**
يمكنك إرسال رسالة مفصلة للإدمن
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📨 إرسال رسالة للإدمن", callback_data='send_to_admin'),
                    InlineKeyboardButton("✅ المشكلة حُلت", callback_data='problem_solved')
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data='tech_support')]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def send_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إرسال رسالة للإدمن"""
        query = update.callback_query
        await query.answer()
        
        category = context.user_data.get('support_category', 'other')
        
        # حفظ تفاصيل المشكلة
        context.user_data['support_problem'] = SupportSystem.AUTO_RESPONSES.get(category, {}).get('question', 'مشكلة أخرى')
        
        await query.edit_message_text(
            f"📨 **إرسال رسالة للإدمن**\n\n"
            f"🔧 **نوع المشكلة:** {SupportSystem.AUTO_RESPONSES.get(category, {}).get('question', 'مشكلة أخرى')}\n\n"
            f"📝 **يرجى كتابة رسالتك المفصلة:**\n"
            f"• وصف المشكلة\n"
            f"• رقم المعاملة إن وجد\n"
            f"• أي معلومات أخرى مفيدة\n\n"
            f"⏰ **وقت الرد المتوقع:** 24 ساعة",
            parse_mode='Markdown'
        )
        
        return SUPPORT_MESSAGE
    
    @staticmethod
    async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة رسالة الدعم"""
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        # حفظ الرسالة
        context.user_data['support_message'] = message_text
        
        # إرسال للإدمن
        try:
            admin_id = config.telegram.ADMIN_TELEGRAM_ID
            
            user_info = await helpers.getInfo(update, context)
            
            admin_message = f"""
📨 **طلب دعم فني جديد**

👤 **المستخدم:** {user_info[1]}
🆔 **المعرف:** {user_id}
🔧 **نوع المشكلة:** {context.user_data.get('support_problem', 'غير محدد')}

📝 **الرسالة:**
{message_text}

📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """
            
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Support message sent to admin from user {user_id}")
            
            # إشعار المستخدم
            await update.message.reply_text(
                "✅ **تم إرسال رسالتك للإدمن بنجاح**\n\n"
                "⏰ **وقت الرد المتوقع:** 24 ساعة\n"
                "📞 **للاستفسار:** @{}".format(config.telegram.ADMIN_TELEGRAM_ID),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending support message: {e}")
            await update.message.reply_text(
                "❌ **حدث خطأ في إرسال الرسالة**\n\n"
                "يرجى المحاولة مرة أخرى أو التواصل مباشرة مع الإدمن.",
                parse_mode='Markdown'
            )
        
        # تنظيف البيانات
        context.user_data.clear()
        
        return ConversationHandler.END
    
    @staticmethod
    async def problem_solved(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """المشكلة حُلت"""
        query = update.callback_query
        await query.answer("✅ شكراً لك على التواصل", show_alert=True)
        
        await query.edit_message_text(
            "🎉 **نشكرك على استخدام نظام الدعم**\n\n"
            "نتمنى لك تجربة ممتعة مع iChancy Bot\n\n"
            "🔙 العودة للقائمة الرئيسية",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='back_to_menu')]
            ]),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def direct_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """التواصل المباشر"""
        query = update.callback_query
        await query.answer()
        
        message = """
📞 **التواصل المباشر**

🔗 **روابط التواصل الرسمية:**

📱 **الدعم الفني للموقع:**
https://www.ichancy.com/ar/contact-us

📧 **البريد الإلكتروني:**
support@ichancy.com

🌐 **صفحة الفيسبوك:**
https://www.facebook.com/ichancy.co

📱 **قناة التليجرام:**
https://t.me/jado_ichancy

🎯 **للاستفسارات العاجلة:**
• استخدم الرابط المباشر أعلاه
• تواصل مع الدعم الفني
• اذكر رقم مستخدمك: {}
        """.format(query.from_user.id)
        
        keyboard = [
            [
                InlineKeyboardButton("🌐 الدعم المباشر", url="https://direct.lc.chat/16220229/"),
                InlineKeyboardButton("📧 البريد", url="mailto:support@ichancy.com")
            ],
            [
                InlineKeyboardButton("📱 فيسبوك", url="https://www.facebook.com/ichancy.co"),
                InlineKeyboardButton("📞 تليجرام", url="https://t.me/ichancy_support")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='contact_us')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def handle_support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استدعاءات نظام الدعم"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'contact_us':
            await SupportSystem.contact_us_menu(update, context)
        elif data == 'faq_menu':
            await SupportSystem.faq_menu(update, context)
        elif data.startswith('faq_'):
            await SupportSystem.show_faq_answer(update, context)
        elif data == 'tech_support':
            await SupportSystem.tech_support_start(update, context)
        elif data.startswith('support_'):
            await SupportSystem.handle_support_category(update, context)
        elif data == 'send_to_admin':
            await SupportSystem.send_to_admin(update, context)
        elif data == 'problem_solved':
            await SupportSystem.problem_solved(update, context)
        elif data == 'direct_contact':
            await SupportSystem.direct_contact(update, context)
    
    @staticmethod
    def get_conversation_handler():
        """الحصول على معالج محادثة الدعم"""
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(SupportSystem.send_to_admin, pattern='^send_to_admin$')],
            states={
                SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, SupportSystem.handle_support_message)]
            },
            fallbacks=[CommandHandler('cancel', SupportSystem.cancel_support)],
            per_message=False,
            per_chat=True,
            per_user=True,
            allow_reentry=True,
        )
    
    @staticmethod
    async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء طلب الدعم"""
        context.user_data.clear()
        await update.message.reply_text(
            "❌ **تم إلغاء طلب الدعم**\n\n"
            "يمكنك العودة للقائمة الرئيسية",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='back_to_menu')]
            ])
        )
        return ConversationHandler.END

# دالة لمعالجة الرسائل من الإدمن للمستخدمين
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رد الإدمن على رسائل المستخدمين"""
    # هذه الدالة يمكن تنفيذها لاحقاً عند إنشاء لوحة الإدمن المتكاملة
    pass
