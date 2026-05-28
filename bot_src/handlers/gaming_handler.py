"""
ichancy.com - معالج الألعاب والجاكبوت
"""

import logging
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import store
import config.telegram
import handlers.ichancy
from utils import helpers
import Logger
logger = Logger.getLogger()

class GamingHandler:
    @staticmethod
    async def handle_gaming_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        message = "🎲 نظام الألعاب والجاكبوت"
        keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')]]

        try:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error in handle_gaming_callback: {e}")
            await query.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    @staticmethod
    async def jackpot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """قائمة الجاكبوت الرئيسية"""
        try:
            def get_user_display_name(user):
                if hasattr(user, 'username') and user.username:
                    return f"@{user.username}"
                elif hasattr(user, 'full_name') and user.full_name:
                    return user.full_name
                else:
                    return f"User_{user.id}"

            def format_currency(amount):
                try:
                    return f"{amount:,.0f} ليرة"
                except:
                    return f"{amount} ليرة"

            try:
                from handlers.admin_handler import AdminHandler
                jackpot_winners = AdminHandler.JACKPOT_WINNERS

                winners_text = ""
                if jackpot_winners:
                    winners_text = "\n🏆 **آخر الفائزين:**\n"
                    for i, winner_id in enumerate(jackpot_winners[-3:], 1):
                        winners_text += f"{i}️⃣ {winner_id}\n"
                else:
                    winners_text = "\n🎯 **كن أول الفائزين!**\n"
            except:
                winners_text = "\n🏆 **آخر الفائزين:**\n1. 🥇 الفائز الأول - 250,000 ليرة\n"

            current_jackpot = 500000

            message = f"""ichancy.com - الجاكبوت 🎲

💎 **قيمة الجاكبوت الحالية:** {format_currency(current_jackpot)}

{winners_text}

🎯 **كيف تلعب:**
• ادخل إلى موقع ichancy.com
• العب في الكازينو أو الرهانات الرياضية
• كل رهان يساهم في الجاكبوت
• اربح الجاكبوت الكامل بالحظ!

🌟 **مميزات خاصة:**
• جاكبوت متراكم يومياً
• فرص فوز عادلة للجميع
• مكافآت إضافية للفائزين

🔗 **العب الآن على ichancy.com**
            """

            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=GamingHandler.create_jackpot_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=GamingHandler.create_jackpot_keyboard(),
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"خطأ في عرض قائمة الجاكبوت: {str(e)}")
            error_message = "❌ حدث خطأ في تحميل معلومات الجاكبوت. يرجى المحاولة لاحقاً."
            if update.callback_query:
                try:
                    await update.callback_query.edit_message_text(
                        error_message,
                        reply_markup=GamingHandler.create_jackpot_keyboard()
                    )
                except Exception:
                    await update.callback_query.message.reply_text(
                        error_message,
                        reply_markup=GamingHandler.create_jackpot_keyboard()
                    )
            else:
                await update.message.reply_text(
                    error_message,
                    reply_markup=GamingHandler.create_jackpot_keyboard()
                )

    @staticmethod
    def create_jackpot_keyboard():
        """إنشاء لوحة مفاتيح قائمة الجاكبوت"""
        keyboard = [
            [
                InlineKeyboardButton("💰 قيمة الجاكبوت", callback_data='jackpot_value'),
                InlineKeyboardButton("🏆 آخر الفائزين", callback_data='jackpot_winners')
            ],
            [
                InlineKeyboardButton("🎰 ألعاب الكازينو", callback_data='casino_games'),
                InlineKeyboardButton("⚽ الرهانات الرياضية", callback_data='sports_betting')
            ],
            [
                InlineKeyboardButton("📜 سجل الرهانات", callback_data='betting_history'),
                InlineKeyboardButton("🎁 العروض والمكافآت", callback_data='promotions')
            ],
            [
                InlineKeyboardButton("👑 برنامج VIP", callback_data='vip_program'),
                InlineKeyboardButton("💬 الدعم المباشر", callback_data='live_support')
            ],
            [
                InlineKeyboardButton("🌐 افتح موقع iChancy", callback_data='open_ichancy'),
                InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    async def betting_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """سجل الرهانات"""
        user_id = str(update.effective_user.id)

        message = """
📜 **سجل الرهانات**

❌ **لا توجد رهانات مسجلة حتى الآن**

🎯 **ابدأ اللعب على iChancy.com لتسجيل رهاناتك هنا!**

🔗 **رابط الموقع:**
https://www.ichancy.com

💰 **كيفية التسجيل:**
1. ادخل إلى الموقع
2. سجل حسابك
3. اربط حسابك بالبوت
4. ابدأ اللعب واربح!
        """

        keyboard = [
            [
                InlineKeyboardButton("🎰 ابدأ اللعب الآن", url="https://www.ichancy.com"),
                InlineKeyboardButton("🔗 ربط الحساب", callback_data='link_account')
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    @staticmethod
    async def casino_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ألعاب الكازينو"""
        message = """
🎰 **iChancy.com - ألعاب الكازينو**

🌟 **الألعاب المتاحة:**

🎲 **الألعاب السريعة:**
• Crash - تحدي التوقيت المثالي
• Dice - خمن الرقم التالي
• Wheel - عجلة الحظ
• Mines - تجنب الألغام

🃏 **ألعاب الطاولة:**
• Blackjack - 21
• Roulette - الروليت
• Baccarat - الباكارات
• Poker - البوكر

🎰 **ماكينات القمار:**
• Slots - مئات الألعاب
• Megaways - فوز ضخم
• Progressive - جاكبوت متراكم

🎪 **الكازينو المباشر:**
• موزعين حقيقيين
• بث مباشر عالي الجودة
• تفاعل مع اللاعبين

🔗 **اللعب الآن على:**
https://www.ichancy.com/casino
        """

        keyboard = [
            [
                InlineKeyboardButton("🎲 ألعاب سريعة", url="https://www.ichancy.com/casino/instant"),
                InlineKeyboardButton("🃏 طاولة", url="https://www.ichancy.com/casino/table")
            ],
            [
                InlineKeyboardButton("🎰 ماكينات", url="https://www.ichancy.com/casino/slots"),
                InlineKeyboardButton("🎪 مباشر", url="https://www.ichancy.com/casino/live")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    @staticmethod
    async def sports_betting(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """الرهانات الرياضية"""
        message = """
⚽ **iChancy.com - الرهانات الرياضية**

🏆 **الرياضات المتاحة:**

⚽ **كرة القدم:**
• الدوريات الأوروبية
• كأس العالم
• دوري أبطال أوروبا
• الدوريات المحلية

🏀 **كرة السلة:**
• NBA
• EuroLeague
• الدوريات المحلية

🎾 **التنس:**
• بطولات الجراند سلام
• ATP & WTA Tours

🏈 **رياضات أخرى:**
• كرة القدم الأمريكية
• الهوكي
• البيسبول
• الملاكمة

📊 **أنواع الرهانات:**
• نتيجة المباراة
• عدد الأهداف
• الهداف الأول
• رهانات مباشرة

🔗 **الرهان الآن على:**
https://www.ichancy.com/sports
        """

        keyboard = [
            [
                InlineKeyboardButton("⚽ كرة قدم", url="https://www.ichancy.com/sports/football"),
                InlineKeyboardButton("🏀 سلة", url="https://www.ichancy.com/sports/basketball")
            ],
            [
                InlineKeyboardButton("🎾 تنس", url="https://www.ichancy.com/sports/tennis"),
                InlineKeyboardButton("🏈 أخرى", url="https://www.ichancy.com/sports/others")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    @staticmethod
    async def promotions_bonuses(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """العروض والمكافآت"""
        message = """
🎁 **iChancy.com - العروض والمكافآت**

🌟 **مكافآت الكازينو:**

💰 **مكافأة الترحيب:**
• 100% على أول إيداع
• حتى 1000 وحدة مجانية
• 50 دورة مجانية

🎰 **مكافآت يومية:**
• مكافأة إعادة التحميل
• دورات مجانية يومية
• كاش باك أسبوعي

⚽ **مكافآت الرياضة:**

🏆 **مكافأة الرهان الأول:**
• رهان مجاني بقيمة 100 وحدة
• تأمين على الرهان الأول

📈 **عروض خاصة:**
• مضاعف الأرباح
• رهانات مجانية
• مكافآت الكومبو

🎯 **برنامج الولاء:**
• نقاط مع كل رهان
• مستويات VIP
• مكافآت حصرية
• مدير حساب شخصي

🔗 **احصل على مكافآتك من:**
https://www.ichancy.com/promotions
        """

        keyboard = [
            [
                InlineKeyboardButton("💰 مكافأة الترحيب", url="https://www.ichancy.com/promotions/welcome"),
                InlineKeyboardButton("🎰 يومية", url="https://www.ichancy.com/promotions/daily")
            ],
            [
                InlineKeyboardButton("🏆 رياضية", url="https://www.ichancy.com/promotions/sports"),
                InlineKeyboardButton("👑 VIP", url="https://www.ichancy.com/promotions/vip")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    @staticmethod
    async def vip_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """برنامج VIP"""
        user_id = str(update.effective_user.id)

        vip_level = "🆕 مبتدئ"
        benefits = """
• مكافأة ترحيب
• دعم عادي
• العب أكثر للترقية!
        """

        message = f"""
👑 **iChancy.com - برنامج VIP**

🏆 **مستواك الحالي:** {vip_level}

💰 **إجمالي رهاناتك:** 0 ليرة

🎁 **مزاياك الحالية:**
{benefits}

📈 **التقدم للمستوى التالي:**
🎯 **المستوى التالي:** 🥉 برونز
💪 **تحتاج:** 5,000 ليرة رهان إضافي

🌟 **كيفية كسب النقاط:**
• كل رهان = نقاط VIP
• العب أكثر = مستوى أعلى
• مستوى أعلى = مزايا أكثر

🔗 **ارتقِ بمستواك على:**
https://www.ichancy.com/vip
        """

        keyboard = [
            [
                InlineKeyboardButton("📊 مستويات VIP", url="https://www.ichancy.com/vip/levels"),
                InlineKeyboardButton("🎁 مكافآت", url="https://www.ichancy.com/vip/rewards")
            ],
            [
                InlineKeyboardButton("👑 ترقيتي", callback_data='my_vip'),
                InlineKeyboardButton("📈 تقدمي", callback_data='vip_progress')
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    @staticmethod
    async def live_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """الدعم المباشر"""
        message = """
💬 **iChancy.com - الدعم المباشر**

🕐 **متاح 24/7**

📞 **طرق التواصل:**

💬 **الدردشة المباشرة:**
• متاح على الموقع
• رد فوري
• دعم متعدد اللغات

📧 **البريد الإلكتروني:**
• support@ichancy.com
• رد خلال ساعة

📱 **التليجرام:**
• @ichancy_support
• دعم سريع

🔗 **الموقع الرسمي:**
• ichancy.com
• قسم المساعدة الشامل

❓ **الأسئلة الشائعة:**
• كيفية الإيداع والسحب
• قوانين الألعاب
• شروط المكافآت
• حل المشاكل التقنية

🛡️ **الأمان والخصوصية:**
• تشفير SSL
• حماية البيانات
• لعب مسؤول

🔗 **تواصل معنا على:**
https://www.ichancy.com/support
        """

        keyboard = [
            [
                InlineKeyboardButton("💬 دردشة مباشرة", url="https://www.ichancy.com/support/chat"),
                InlineKeyboardButton("📧 بريد", url="mailto:support@ichancy.com")
            ],
            [
                InlineKeyboardButton("📱 تليجرام", url="https://t.me/ichancy_support"),
                InlineKeyboardButton("❓ أسئلة شائعة", url="https://www.ichancy.com/faq")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    @staticmethod
    async def open_ichancy_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فتح موقع iChancy"""
        message = """
🌐 **موقع iChancy.com**

🔗 **الرابط الرسمي:**
https://www.ichancy.com

🎯 **ما ستجده:**
• ألعاب كازينو متنوعة
• رهانات رياضية شاملة
• مكافآت وعروض حصرية
• دعم فني متميز

🎁 **عروض خاصة لمستخدمي البوت:**
• مكافأة ترحيب مضاعفة
• رهانات مجانية
• كاش باك إضافي

⚡ **ابدأ اللعب الآن:**
1. اضغط على الرابط أعلاه
2. سجل حسابك
3. اربط حسابك بالبوت
4. احصل على مكافآتك

🔒 **آمن ومرخص بالكامل**
        """

        keyboard = [
            [
                InlineKeyboardButton("🌐 زيارة الموقع", url="https://www.ichancy.com"),
                InlineKeyboardButton("📱 تطبيق", url="https://www.ichancy.com/app")
            ],
            [
                InlineKeyboardButton("🎰 كازينو", url="https://www.ichancy.com/casino"),
                InlineKeyboardButton("⚽ رياضة", url="https://www.ichancy.com/sports")
            ],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    @staticmethod
    async def handle_gaming_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استدعاءات نظام الألعاب"""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == 'jackpot':
            await GamingHandler.jackpot_menu(update, context)
        elif data == 'betting_history':
            await GamingHandler.betting_history(update, context)
        elif data == 'casino_games' or data == 'live_casino':
            await GamingHandler.casino_games(update, context)
        elif data == 'sports_betting':
            await GamingHandler.sports_betting(update, context)
        elif data == 'promotions' or data == 'gaming_promotions':
            await GamingHandler.promotions_bonuses(update, context)
        elif data == 'vip_program':
            await GamingHandler.vip_program(update, context)
        elif data == 'live_support':
            await GamingHandler.live_support(update, context)
        elif data == 'open_ichancy':
            await GamingHandler.open_ichancy_website(update, context)
        elif data == 'jackpot_value':
            try:
                await query.edit_message_text(
                    "💰 **قيمة الجاكبوت الحالية:** 500,000 ليرة\n\n"
                    "📈 **آخر تحديث:** اليوم\n"
                    "🎯 **الحد الأدنى للفوز:** 50,000 ليرة\n\n"
                    "🔗 **شارك الآن:** https://www.ichancy.com/jackpot",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in jackpot_value: {e}")
        elif data == 'jackpot_winners':
            try:
                from handlers.admin_handler import AdminHandler
                jackpot_winners = AdminHandler.JACKPOT_WINNERS

                if not jackpot_winners:
                    message_text = "🏆 **لا يوجد فائزين مسجلين بعد**\n\n🎯 **كن أول الفائزين!**"
                else:
                    message_text = "🏆 **آخر الفائزين بالجاكبوت:**\n\n"
                    for i, winner_id in enumerate(jackpot_winners, 1):
                        message_text += f"{i}️⃣ {winner_id}\n"
                    message_text += f"\n🎉 **إجمالي الفائزين:** {len(jackpot_winners)}"
            except:
                message_text = "🏆 **آخر الفائزين بالجاكبوت:**\n\n1. 🥇 الفائز الأول - 250,000 ليرة\n2. 🥈 الفائز الثاني - 150,000 ليرة\n3. 🥉 الفائز الثالث - 100,000 ليرة\n\n🎉 **كن الفائز القادم!**"

            try:
                await query.edit_message_text(
                    message_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 رجوع", callback_data='jackpot')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in jackpot_winners: {e}")
        elif data == 'link_account':
            try:
                await query.edit_message_text(
                    "🔗 **ربط حساب iChancy بالبوت**\n\n"
                    "1. سجل في iChancy.com\n"
                    "2. احصل على معرف لاعبك (Player ID)\n"
                    "3. أرسل المعرف في هذه المحادثة\n"
                    "4. سيتم ربط حسابك تلقائياً\n\n"
                    "💰 **مزايا الربط:**\n"
                    "• متابعة رهاناتك\n"
                    "• جاكبوت تلقائي\n"
                    "• مكافآت حصرية",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🌐 iChancy.com", url="https://www.ichancy.com")],
                        [InlineKeyboardButton("🔙 رجوع", callback_data='betting_history')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in link_account: {e}")
        elif data == 'my_vip':
            try:
                await query.edit_message_text(
                    "👑 **معلومات VIP الخاصة بك**\n\n"
                    "🏆 **المستوى:** مبتدئ\n"
                    "💰 **النقاط:** 0 نقطة\n"
                    "🎯 **للترقية:** 5,000 ليرة\n\n"
                    "🔗 **تعرف أكثر على:** https://www.ichancy.com/vip",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 رجوع", callback_data='vip_program')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in my_vip: {e}")
        elif data == 'vip_progress':
            try:
                await query.edit_message_text(
                    "📈 **تقدمك في برنامج VIP**\n\n"
                    "📊 **الرهانات المطلوبة:**\n"
                    "• 🥉 برونز: 5,000 ليرة\n"
                    "• 🥈 فضة: 20,000 ليرة\n"
                    "• 🥇 ذهب: 50,000 ليرة\n"
                    "• 💎 ماس: 100,000 ليرة\n\n"
                    "💰 **رهاناتك الحالية:** 0 ليرة",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 رجوع", callback_data='vip_program')]
                    ]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in vip_progress: {e}")
