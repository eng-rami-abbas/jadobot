"""
معالج الإحالات والهدايا
"""

import logging
import random
import string
from datetime import datetime, timedelta
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

import store
import config.telegram
import handlers.ichancy
from utils import helpers

logger = logging.getLogger(__name__)

class ReferralHandler:
    """معالج الإحالات"""
    
    @staticmethod
    def generate_referral_code(user_id: str, length: int = 8) -> str:
        """توليد كود إحالة فريد"""
        # استخدام آخر 4 أرقام من user_id + حروف عشوائية
        user_suffix = str(user_id)[-4:] if len(str(user_id)) >= 4 else str(user_id).zfill(4)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length-4))
        return f"REF{user_suffix}{random_chars}"
    
    @staticmethod
    async def show_referral_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصاءات الإحالات"""
        user_id = str(update.effective_user.id)
        
        # الحصول على معلومات المستخدم
        user = store.getUserByTelegramId(user_id)
        if not user:
            # إنشاء المستخدم إذا لم يكن موجوداً
            try:
                store.insertNewUser(user_id, update.effective_user.username or "مستخدم")
                user = store.getUserByTelegramId(user_id)
            except Exception:
                pass

        # توليد كود إحالة إذا لم يكن موجوداً
        referral_code = helpers.generate_referral_code(user_id)

        # إنشاء رابط الإحالة
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        # رسالة الإحالة
        stats_message = f"""
📊 **إحصاءات نظام الإحالات**

🔗 **رابط الإحالة الخاص بك:**
 قم بنسخ رابط الاحالة الخاص بك عن طريق الضغط على خيار رابط الاحالة الخاص بي
`{referral_link}`

💎 **مزايا نظام الإحالات:**
• ربح {handlers.ichancy.REFERRAL_PERCENTAGE}% من أول إيداع لكل شخص تحيله
• مكافأة إضافية عند إحالة 3 أشخاص
• متابعة مباشرة لجميع الإحالات

💰 **إحصائياتك الحالية:**
👥 عدد الإحالات: 0
💵 أرباح الإحالات: 0
📊 مستوى الإحالة: مبتدئ

📋 **كيفية الاستفادة:**
1. شارك الرابط مع أصدقائك
2. اطلب منهم استخدام الرابط لبدء البوت
3. عندما يقومون بأول إيداع، تحصل على {handlers.ichancy.REFERRAL_PERCENTAGE}%
4. تتبع أرباحك في لوحة الإحالة

🎯 **مستويات الإحالة:**
🏅 مبتدئ: 0-2 إحالة
🥈 محترف: 3-10 إحالة
🥇 خبير: 11+ إحالة
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 تفاصيل الإحالات", callback_data='referral_details'),
            ],
            [
                InlineKeyboardButton("💰 أرباحي من الإحالات", callback_data='referral_earnings'),
                InlineKeyboardButton("👥 أحالتي", callback_data='my_referrals')
            ],
            [
                InlineKeyboardButton("🏆 مسابقات الإحالة", callback_data='referral_contest'),
                InlineKeyboardButton("📈 ترتيبي", callback_data='referral_rank')
            ],
            [
                InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    stats_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception:
                await update.callback_query.message.reply_text(
                    stats_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                stats_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def share_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مشاركة رابط الإحالة"""
        user_id = str(update.effective_user.id)
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        share_message = f"""
🌟 **انضم إلى iChancy Bot واحصل على مكافآت!**

🔗 رابط التسجيل الخاص بي:
{referral_link}

💎 **مميزات البوت:**
✅ إنشاء حسابات iChancy تلقائياً
✅ إيداع وسحب بسيط وسريع
✅ دعم 24/7
✅ نظام إحالة بربح {handlers.ichancy.REFERRAL_PERCENTAGE}%

🚀 **انضم الآن وابدأ الربح!**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📋 نسخ الرابط", callback_data='copy_referral_link')
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data='referral')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        try:
            await query.edit_message_text(
                "📤 **شارك رابط الإحالة الآن**\n\nاضغط على زر النسخ لنسخ الرابط:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception:
            await query.message.reply_text(
                "📤 **شارك رابط الإحالة الآن**\n\nاضغط على زر النسخ لنسخ الرابط:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def copy_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نسخ رابط الإحالة"""
        user_id = str(update.effective_user.id)
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        await update.callback_query.answer(
            f"✅ تم نسخ الرابط: {referral_link}",
            show_alert=True
        )
    
    @staticmethod
    async def handle_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استدعاءات نظام الإحالة"""
        query = update.callback_query

        data = query.data
        
        if data == 'referral':
            await ReferralHandler.show_referral_stats(update, context)
        elif data == 'share_referral':
            await ReferralHandler.share_referral_link(update, context)
        elif data == 'copy_referral_link':
            await ReferralHandler.copy_referral_link(update, context)
        elif data == 'referral_details':
            try:
                await query.edit_message_text(
                    "📊 **تفاصيل نظام الإحالة**\n\n"
                    "• نسبة الربح: 10% من أول إيداع\n"
                    "• الحد الأدنى للإيداع: 10,000 ليرة\n"
                    "• المكافآت الشهرية لأكثر الإحالات\n"
                    "• المسابقات الأسبوعية\n\n"
                    "🔙 العودة للقائمة الرئيسية للإحالة",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in referral_details: {e}")
        elif data == 'referral_earnings':
            try:
                await query.edit_message_text(
                    "💰 **أرباحي من الإحالات**\n\n"
                    "📅 اليوم: 0 ليرة\n"
                    "📅 هذا الأسبوع: 0 ليرة\n"
                    "📅 هذا الشهر: 0 ليرة\n"
                    "💰 الإجمالي: 0 ليرة\n\n"
                    "🔙 العودة للقائمة الرئيسية للإحالة",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in referral_earnings: {e}")
        elif data == 'my_referrals':
            try:
                await query.edit_message_text(
                    "👥 **قائمة أحالتي**\n\n"
                    "📭 لا توجد إحالات حتى الآن\n\n"
                    "🔗 شارك رابط الإحالة لبدء الربح!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 مشاركة الرابط", callback_data='share_referral')],
                        [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in my_referrals: {e}")
        elif data == 'referral_contest':
            try:
                await query.edit_message_text(
                    "🏆 **مسابقة هذا الشهر**\n\n"
                    "🥇 المركز الأول: 50,000 ليرة\n"
                    "🥈 المركز الثاني: 30,000 ليرة\n"
                    "🥉 المركز الثالث: 20,000 ليرة\n\n"
                    "📅 تنتهي المسابقة في نهاية الشهر\n"
                    "📊 المنافسة ساخنة! شارك الآن",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 شارك الآن", callback_data='share_referral')],
                        [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in referral_contest: {e}")
        elif data == 'referral_rank':
            try:
                await query.edit_message_text(
                    "📈 **ترتيبي الشهري**\n\n"
                    "🏆 ترتيبك الحالي: غير محدد\n"
                    "👥 عدد الإحالات: 0\n"
                    "💰 أرباحك: 0 ليرة\n\n"
                    "🔥 تنافس مع الآخرين واربح جوائز!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 زيادة الإحالات", callback_data='share_referral')],
                        [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in referral_rank: {e}")
        elif data == 'gift_system':
            try:
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
                            InlineKeyboardButton("🎫 كود هدية", callback_data='gift_code')
                        ],
                        [InlineKeyboardButton("🔙 رجوع", callback_data='referral')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in gift_system: {e}")
        elif data == 'referral_image' or data == 'referral_text':
            try:
                user_id = str(update.effective_user.id)
                bot_username = context.bot.username
                referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
                await query.answer(
                    f"📋 رابط الإحالة: {referral_link}",
                    show_alert=True
                )
            except Exception as e:
                logger.error(f"Error in referral_image/text: {e}")
