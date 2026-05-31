"""
نظام الإحالة والهدايا المتكامل
"""

import logging
import random
import string
from datetime import datetime
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

import store
import config.telegram
import handlers.ichancy
from utils import helpers

logger = logging.getLogger(__name__)

class ReferralSystem:
    """نظام الإحالة والهدايا"""
    
    @staticmethod
    async def handle_referral_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بدء الإحالة"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        
        # التحقق من وجود معلمة الإحالة في الأمر /start
        if context.args and len(context.args) > 0:
            ref_param = context.args[0]
            if ref_param.startswith('ref_'):
                referrer_id = ref_param.replace('ref_', '')
                
                # التحقق من أن المحيل ليس نفس المستخدم
                if referrer_id != user_id:
                    # توليد كود إحالة للمستخدم الجديد
                    referral_code = helpers.generate_referral_code(user_id)
                    
                    # حفظ معلومات الإحالة
                    store.update_user_referral_info(
                        telegram_id=user_id,
                        referral_code=referral_code,
                        referred_by=referrer_id
                    )
                    
                    # إضافة ترحيب خاص بالإحالة
                    welcome_message = f"""
🎉 **مرحباً بك عبر رابط الإحالة!**

👤 تمت إحالتك بواسطة: {referrer_id}
🔗 كود إحالتك: {referral_code}

نظام احالات Ichancy Bot
يقدّم لك فرصة لدخل إضافي كل 10 أيام .
كن وكيلاً معنا بأبسط طريقة
إحصل على نسبة ثابتة لكل عمليات الشحن والتعبئة القادمة عن طريق رابط احالتك ضمن البوت 
.....
1-عند الدخول الى البوت قم بنسخ رابط الاحالة الخاص بك عن طريق الضغط على خيار رابط الاحالة الخاص بي
2- عندما تقوم بنشر رابط احالتك ويقوم أحد بالتسجيل عن طريقة سنبدأ بحساب نسبة ثابتة لجميع عمليات السحب والتعبئة عن طريقك . 
3-يمكن الاطلاع على عدد الاحالات التي قامت بالتسجيل من خلال الرابط الخاص بك عن طريق الضغط على خيار عدد الاحالات الخاصة بك خلال المسابقة الحالية 
4- يتم حساب الارباح عند وجود 3 إحالات نشطة او أكثر
ماذا تنتظر...! 
توزيع النسب كل 10 أيام

🚀 استمتع بتجربة iChancy!
                    """
                    
                    await update.message.reply_text(
                        welcome_message,
                        parse_mode='Markdown',
                        reply_markup=helpers.getReplyMarkup(user_id)
                    )
                    
                    logger.info(f"User {user_id} joined via referral from {referrer_id}")
                    return
        
        # التسجيل العادي بدون إحالة
        store.insertNewUser(user_id, username)
        
        # توليد كود إحالة للمستخدم الجديد
        referral_code = helpers.generate_referral_code(user_id)
        store.update_user_referral_info(
            telegram_id=user_id,
            referral_code=referral_code
        )
    
    @staticmethod
    async def show_referral_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة الإحالة"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        
        # الحصول على إحصائيات الإحالة
        stats = store.get_referral_stats(user_id)
        
        if not stats:
            stats = {
                'referral_code': helpers.generate_referral_code(user_id),
                'referral_count': 0,
                'referral_earnings': 0,
                'referrals': []
            }
        
        bot_username = context.bot.username
        referral_link = f"https://t.me/@jado93_bot?start=ref_{user_id}"
        
        # بناء رسالة لوحة الإحالة
        message = f"""
📊 **لوحة الإحالة والهدايا**

🔗 **كود إحالتك:** `{stats['referral_code']}`
👥 **عدد أحالتك:** {stats['referral_count']}
💰 **أرباح الإحالة:** {stats['referral_earnings']:,} ليرة

🔗 **رابط الإحالة الخاص بك:**
`{referral_link}`

🎁 **مكافآت الإحالة:**
• ربح 10% من أول إيداع لكل شخص تحيله
• مكافأة 5,000 ليرة عند إحالة 5 أشخاص
• جوائز شهرية لأكثر الأشخاص إحالة

📈 **أحالتك الأخيرة:**
        """
        
        if stats['referrals']:
            for i, referral in enumerate(stats['referrals'], 1):
                username = referral['telegram_username'] or "مستخدم جديد"
                date = referral['created_at'].strftime("%Y-%m-%d") if referral['created_at'] else "غير معروف"
                message += f"\n{i}. {username} - {date}"
        else:
            message += "\n📭 لا توجد إحالات حتى الآن"
        
        # أزرار لوحة الإحالة
        keyboard = [
            [
                InlineKeyboardButton("📤 مشاركة الرابط", callback_data='share_referral'),
                InlineKeyboardButton("💰 أرباحي", callback_data='referral_earnings')
            ],
            [
                InlineKeyboardButton("🎁 نظام الهدايا", callback_data='gift_system'),
                InlineKeyboardButton("📊 الإحصائيات", callback_data='referral_stats')
            ],
            [
                InlineKeyboardButton("🏆 المسابقات", callback_data='referral_contests'),
                InlineKeyboardButton("📋 قائمة أحالتي", callback_data='my_referrals')
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
    async def share_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مشاركة رابط الإحالة"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        bot_username = context.bot.username
        
        message, referral_link = helpers.get_referral_message(user_id, bot_username)
        
        keyboard = [
            [
                InlineKeyboardButton("📤 مشاركة مباشرة", url=f"tg://msg?text={message}"),
                InlineKeyboardButton("📋 نسخ الرابط", callback_data='copy_referral_link')
            ],
            [
                InlineKeyboardButton("📸 صورة للشير", callback_data='referral_image'),
                InlineKeyboardButton("📝 نص للنسخ", callback_data='referral_text')
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data='referral')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📤 **مشاركة رابط الإحالة**\n\n"
            "اختر طريقة المشاركة المناسبة لك:",
            reply_markup=reply_markup
        )
    
    @staticmethod
    async def process_referral_earnings(update: Update, context: ContextTypes.DEFAULT_TYPE, deposit_amount: int, user_id: str):
        """معالجة أرباح الإحالة عند الإيداع"""
        # الحصول على معلومات المستخدم
        user = store.getUserByTelegramId(user_id)
        if not user or not user.get('referred_by'):
            return
        
        referrer_id = user['referred_by']
        
        # حساب أرباح الإحالة (10% من الإيداع)
        referral_earning = int(deposit_amount * 0.10)
        
        # إضافة الأرباح للمحيل
        store.add_referral_earning(referrer_id, referral_earning)
        
        # إشعار المحيل
        try:
            await context.bot.send_message(
                chat_id=int(referrer_id),
                text=f"🎉 **مبروك! ربح جديد من الإحالة**\n\n"
                     f"💰 المبلغ: {referral_earning:,} ليرة\n"
                     f"👤 من: {user.get('telegram_username', 'مستخدم جديد')}\n"
                     f"💵 إجمالي أرباحك: {store.get_referral_stats(referrer_id)['referral_earnings']:,} ليرة"
            )
        except TelegramError as e:
            logger.error(f"Failed to notify referrer: {e}")
        
        logger.info(f"Referral earnings processed: {referrer_id} earned {referral_earning} from {user_id}")
    
    @staticmethod
    async def handle_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استدعاءات نظام الإحالة"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'referral':
            await ReferralSystem.show_referral_dashboard(update, context)
        elif data == 'share_referral':
            await ReferralSystem.share_referral_link(update, context)
        elif data == 'copy_referral_link':
            user_id = str(update.effective_user.id)
            bot_username = context.bot.username
            referral_link = f"https://t.me/@jado93_bot?start=ref_{user_id}"
            
            await query.answer(
                f"✅ تم نسخ الرابط: {referral_link}",
                show_alert=True
            )
        elif data == 'referral_earnings':
            user_id = str(update.effective_user.id)
            stats = store.get_referral_stats(user_id)
            
            message = f"""
💰 **أرباح الإحالة التفصيلية**

📅 **إجمالي الأرباح:** {stats['referral_earnings']:,} ليرة
👥 **عدد الإحالات:** {stats['referral_count']}

📊 **التوزيع الشهري:**
• هذا الشهر: {stats['referral_earnings']:,} ليرة
• الشهر الماضي: 0 ليرة

🎯 **أهداف القادمة:**
• 5 إحالات: 5,000 ليرة مكافأة
• 10 إحالات: 15,000 ليرة مكافأة
• 20 إحالة: 30,000 ليرة مكافأة
            """
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                ]),
                parse_mode='Markdown'
            )
        elif data == 'gift_system':
            await query.edit_message_text(
                "🎁 **نظام الهدايا والإهداء**\n\n"
                "✨ **ميزات النظام:**\n"
                "• إهداء الرصيد للأصدقاء\n"
                "• أكواد هدايا قابلة للاستخدام\n"
                "• عروض وخصومات حصرية\n"
                "• مسابقات وجوائز أسبوعية\n\n"
                "🔙 العودة للوحة الإحالة",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎁 إهداء رصيد", callback_data='send_gift'),
                        InlineKeyboardButton("🎫 كود هدية", callback_data='reseive_gift')
                    ],
                    [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                ]),
                parse_mode='Markdown'
            )