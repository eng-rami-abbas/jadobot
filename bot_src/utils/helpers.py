import Logger
import random
import string
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram import Update
from telegram.ext import ContextTypes
import handlers.admin_handler

logger = Logger.getLogger()

def getTextWelcome(username):
    welcome_text = (
        f"أهلا بك في بوت\n "
        "Jado Ichancy Bot"
    )
    return welcome_text

def generate_referral_code(telegram_id, length=8):
    """توليد كود إحالة فريد"""
    try:
        # استخدام آخر 4 أرقام من telegram_id + أحرف عشوائية
        id_part = str(telegram_id)[-4:].zfill(4)
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length-4))
        return f"REF{id_part}{random_part}"
    except Exception as e:
        logger.error(f"Error generating referral code: {e}")
        return f"REF{telegram_id[-4:]}"

def get_referral_message(telegram_id, bot_username):
    """إنشاء رسالة الإحالة"""
    referral_code = generate_referral_code(telegram_id)
    referral_link = f"https://t.me/{bot_username}?start=ref_{telegram_id}"
    
    message = f"""
🎉 **انضم إلى iChancy واحصل على مكافآت حصرية!**

🔗 **رابط التسجيل الخاص بي:**
{referral_link}

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

عدد الاحالات التابعة لك:  0
رابط الإحالة الخاص بك: 
http://t.me/@Jado93_bot?start=ref_{telegram_id}



⚡️ **مميزات البوت:**
✅ إنشاء حسابات iChancy تلقائياً
✅ إيداع وسحب سريع وآمن
✅ دعم فني 24/7
✅ نظام هدايا وتخفيضات

🚀 **انضم الآن عبر الرابط أعلاه!**
    """
    
    return message, referral_link

def getKeyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton("⚡️ Ichancy", callback_data='ichancy')],
        [
            InlineKeyboardButton("شحن رصيد 📥", callback_data='deposit'),
            InlineKeyboardButton("سحب رصيد 📤", callback_data='withdrawal'),
        ],
        [InlineKeyboardButton("نظام الاحالات 💰", callback_data='referral')],
       
        [
            InlineKeyboardButton("كود هدية 🎁", callback_data='gift_code'),
            InlineKeyboardButton("اهداء رصيد 🎁", callback_data='send_gift')
        ],
       
        [   InlineKeyboardButton(" الجاكبوت والألعاب والبونصات والعروض الحالية 🎲🎁", callback_data='jackpot')
        ],
        
        [   InlineKeyboardButton("السجل 📜", callback_data='log'),
        ],

        [InlineKeyboardButton("اللفة المجانية 🎡", callback_data="spin_wheel")],
        
        [InlineKeyboardButton("تطبيق vpn لتشغيل كامل اقسام الموقع", url="https://t.me/Ichancy_boot_Vbn/3"),
         InlineKeyboardButton("ichancy apk", url="https://android.betcoapps.com/novichok/ichancy_com/ichancy_com.apk")
        ],
        [
            InlineKeyboardButton("رسالة للادمن 📨", callback_data='admin_message'),
            InlineKeyboardButton("تواصل معنا ✉️", callback_data='contact_us')
        ],
        
        [
            InlineKeyboardButton("الشروحات 📝", callback_data='guides'),
            InlineKeyboardButton("الشروط والاحكام 📌", callback_data='terms_and_conditions'),
        ],
        
    ]
    
    # إضافة زر الإدمن إذا كان المستخدم أدمن
    try:
        if user_id and handlers.admin_handler.AdminHandler.is_admin(user_id):
            keyboard.append([InlineKeyboardButton("🔧 لوحة الإدمن", callback_data='admin_panel')])
    except ImportError:
        logger.warning("admin_handler not available yet")
        pass
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
    
    return keyboard

def getReplyMarkup(user_id=None):
    reply_markup = InlineKeyboardMarkup(getKeyboard(user_id))
    return reply_markup

async def getInfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"User {username} ({user_id}) started the bot")
    return user_id, username

def getStatusText(user):
    status_text = (
        "https://www.ichancy.com/ar \n\n"
        f"👤 الدخول: {user['name']}\n"
        f"📧 الإيميل: {user['email']}\n"
        f"🔒 كلمة السر: {user['password']} "
    )
    return status_text

def format_currency(amount: int) -> str:
    """تنسيق العملة"""
    return f"{amount:,}"

def getAdminKeyboard():
    """لوحة أدوات الإدمن المتقدمة"""
    keyboard = [
        [
            InlineKeyboardButton("📊 لوحة التحكم", callback_data='admin_dashboard'),
            InlineKeyboardButton("📈 التحليلات", callback_data='analytics_dashboard')
        ],
        [
            InlineKeyboardButton("🔔 الإشعارات", callback_data='notification_center'),
            InlineKeyboardButton("🔄 النسخ الاحتياطي", callback_data='backup_management')
        ],
        [
            InlineKeyboardButton("👁️ المراقبة", callback_data='monitoring_panel'),
            InlineKeyboardButton("⚙️ الصيانة", callback_data='maintenance_panel')
        ],
        [
            InlineKeyboardButton("🤖 الرد الآلي", callback_data='auto_reply_setup'),
            InlineKeyboardButton("🎫 نظام التذاكر", callback_data='support_tickets')
        ],
        [
            InlineKeyboardButton("📊 تقارير", callback_data='reports'),
            InlineKeyboardButton("🔧 الإعدادات", callback_data='system_settings')
        ],
        [
            InlineKeyboardButton("🏠 الرئيسية", callback_data='back_to_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
