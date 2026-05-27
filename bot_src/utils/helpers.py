import Logger
import random
import string
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram import Update
from telegram.ext import ContextTypes
import handlers.admin_handler

logger = Logger.getLogger()

WHEEL_WEBAPP_URL = os.getenv('WHEEL_WEBAPP_URL', 'https://eng-rami-abbas.github.io/jadobot/')

def get_wheel_webapp_url(telegram_id: str) -> str:
    base = WHEEL_WEBAPP_URL.rstrip('/')
    return f"{base}/index.html?user_id={telegram_id}"

def getTextWelcome(username):
    welcome_text = (
        f"أهلا بك في بوت\n "
        "Jado Ichancy Bot"
    )
    return welcome_text

def generate_referral_code(telegram_id, length=8):
    try:
        id_part = str(telegram_id)[-4:].zfill(4)
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length-4))
        return f"REF{id_part}{random_part}"
    except Exception as e:
        logger.error(f"Error generating referral code: {e}")
        return f"REF{telegram_id[-4:]}"

def get_referral_message(telegram_id, bot_username):
    referral_code = generate_referral_code(telegram_id)
    referral_link = f"https://t.me/{bot_username}?start=ref_{telegram_id}"
    message = f"""
🎉 **انضم إلى iChancy واحصل على مكافآت حصرية!**
...
    """
    return message, referral_link

def getKeyboard(user_id=None):
    # زر اللفة المجانية: WebApp مباشر إذا وجد user_id
    if user_id:
        wheel_url = get_wheel_webapp_url(str(user_id))
        wheel_button = InlineKeyboardButton("اللفة المجانية 🎡", web_app=WebAppInfo(url=wheel_url))
    else:
        wheel_button = InlineKeyboardButton("اللفة المجانية 🎡", callback_data="spin_wheel")

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
        [wheel_button],
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
    
    try:
        if user_id and handlers.admin_handler.AdminHandler.is_admin(user_id):
            keyboard.append([InlineKeyboardButton("🔧 لوحة الإدمن", callback_data='admin_panel')])
    except Exception as e:
        logger.error(f"Error adding admin button: {e}")
    
    return keyboard

def getReplyMarkup(user_id=None):
    return InlineKeyboardMarkup(getKeyboard(user_id))

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
    return f"{amount:,}"

def getAdminKeyboard():
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
