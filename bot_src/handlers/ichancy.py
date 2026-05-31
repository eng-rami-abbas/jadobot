import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes
import Logger
from services.iChancyAPI import iChancyAPI
import supabase_integration as supa
load_dotenv()

logger = Logger.getLogger()

PARENT_ID = os.getenv('PARENT_ID', '2730826')
USERNAME_SUFFIX = '_jado2026'
EXCHANGE_RATE = 50000

API_TIMEOUT = 15
MAX_RETRIES = 2

REFERRAL_PERCENTAGE = 4
REFERRAL_BONUS = {
    5: 5000,
    10: 15000,
    20: 30000
}
MIN_DEPOSIT_FOR_REFERRAL = 10000

MIN_DEPOSIT = 25000
MAX_DEPOSIT = 10000000
MIN_WITHDRAWAL = 10000
MAX_WITHDRAWAL = 5000000

JACKPOT_CONTRIBUTION_RATE = 0.01
MIN_JACKPOT = 100000
JACKPOT_DRAW_TIME = "00:00"

VIP_LEVELS = {
    "bronze": 5000,
    "silver": 20000,
    "gold": 50000,
    "diamond": 100000
}

VIP_BENEFITS = {
    "bronze": "5% كاش باك، مكافأة شهرية، دعم محسن",
    "silver": "10% كاش باك، مكافآت شهرية، دعم سريع",
    "gold": "15% كاش باك، مكافآت أسبوعية، دعم أولوية",
    "diamond": "مدير حساب شخصي، مكافآت يومية، حدود سحب عالية"
}

BACKUP_SCHEDULE = "02:00"
BACKUP_RETENTION_DAYS = 30
BACKUP_PATH = "backups/"

MONITORING_INTERVAL = 300
ALERT_THRESHOLDS = {
    'memory': 80,
    'cpu': 70,
    'disk': 85
}

NOTIFICATION_TYPES = {
    'transaction': '💰 معاملة جديدة',
    'withdrawal': '💸 طلب سحب',
    'deposit': '📥 طلب إيداع',
    'system': '⚙️ نظام',
    'alert': '🚨 تنبيه'
}

ANALYTICS_REFRESH = 3600


def get_api():
    """Get a shared iChancyAPI instance (avoids re-auth on every call)."""
    try:
        return iChancyAPI.get_shared() or iChancyAPI()
    except Exception as e:
        logger.error(f"Failed to create iChancyAPI instance: {e}")
        return None

async def handle_ichancy(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)

    try:
        await query.edit_message_text(
            "🎮 **نظام iChancy**\n\nاختر العملية:",
            reply_markup=get_ichancy_keyboard(user_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in handle_ichancy: {e}")
        await query.message.reply_text(
            "🎮 **نظام iChancy**\n\nاختر العملية:",
            reply_markup=get_ichancy_keyboard(user_id),
            parse_mode="Markdown"
        )


def get_ichancy_account(user_id):
    try:
        # Ensure consistent type - Supabase expects string telegram_id
        account = supa.get_ichancy_details_by_telegram_id(str(user_id))
        if account and account.get("username"):
            return account
    except Exception as e:
        logger.error(f"Error getting ichancy account for user {user_id}: {e}")
        pass
    return None


def get_ichancy_keyboard(user_id):
    account = get_ichancy_account(user_id)
    has_account = bool(account and account.get("username"))

    if has_account:
        keyboard = [
            [
                InlineKeyboardButton("💸 سحب رصيد", callback_data="ichancy_withdraw_adv"),
                InlineKeyboardButton("💰 شحن رصيد", callback_data="ichancy_deposit_adv"),
            ],
            [InlineKeyboardButton("⚡ شحن كامل الرصيد", callback_data="ichancy_deposit_all_adv")],
            [InlineKeyboardButton("👤 معلومات الحساب", callback_data="ichancy_account_info")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("➕ إنشاء حساب جديد", callback_data="ichancy_create_account")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")],
        ]

    return InlineKeyboardMarkup(keyboard)


async def ichancy_balance(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    account = get_ichancy_account(user_id)

    if not account or not account.get("username"):
        await query.edit_message_text("❌ يجب أن تنشئ حساب أولا")
        return

    api = get_api()
    if not api:
        await query.edit_message_text("❌ لا يمكن الاتصال بخوادم iChancy حالياً")
        return

    balance_result = await api.get_player_balance_by_username(account["username"])

    if balance_result and balance_result.get('success'):
        balance = balance_result.get('balance', 0)
    else:
        balance = 0

    try:
        await query.edit_message_text(
            f"📊 **رصيدك الحالي:**\n\n💰 {balance}",
            parse_mode="Markdown",
            reply_markup=get_ichancy_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Error in ichancy_balance: {e}")
        await query.message.reply_text(
            f"📊 **رصيدك الحالي:**\n\n💰 {balance}",
            parse_mode="Markdown",
            reply_markup=get_ichancy_keyboard(user_id)
        )

async def delete_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = str(query.from_user.id)
    account = get_ichancy_account(telegram_id)

    if not account or not account.get("username"):
        await query.answer("❌ لا يوجد حساب", show_alert=True)
        return

    try:
        supa.get_client().table("users_ichancy_details").delete().eq("telegram_id", telegram_id).execute()
    except Exception as e:
        logger.warning(f"Could not delete ichancy details from Supabase: {e}")

    try:
        await query.edit_message_text("✅ تم حذف الحساب بنجاح")
    except Exception:
        await query.message.reply_text("✅ تم حذف الحساب بنجاح")

    await query.message.reply_text(
        "🎮 القائمة:",
        reply_markup=get_ichancy_keyboard(int(telegram_id))
    )
