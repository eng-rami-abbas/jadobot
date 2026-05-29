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
        account = supa.get_ichancy_details_by_telegram_id(user_id)
        if account and account.get("username"):
            return account
    except Exception:
        pass
    return None


def get_ichancy_keyboard(user_id):
    account = get_ichancy_account(user_id)
    has_account = bool(account and account.get("username"))

    if has_account:
        keyboard = [
            [InlineKeyboardButton("👤 معلومات الحساب", callback_data="ichancy_account_info")],
            [
                InlineKeyboardButton("💰 شحن رصيد", callback_data="ichancy_deposit_adv"),
                InlineKeyboardButton("💸 سحب رصيد", callback_data="ichancy_withdraw_adv")
            ],
            [InlineKeyboardButton("⚡ شحن كامل الرصيد", callback_data="ichancy_deposit_all_adv")],
            [InlineKeyboardButton("📊 رصيدي", callback_data="ichancy_balance")],
            [InlineKeyboardButton("📈 عملياتي", callback_data="ichancy_transactions")],
            [InlineKeyboardButton("❌ حذف الحساب", callback_data="ichancy_delete_account")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("➕ إنشاء حساب جديد", callback_data="ichancy_create_account")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")],
        ]

    return InlineKeyboardMarkup(keyboard)

async def ichancy_create(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data['ichancy_state'] = 'ichancy_wait_username'
    context.user_data.pop('temp_username', None)

    try:
        await query.edit_message_text("🆕 أدخل اسم المستخدم للحساب:")
    except Exception:
        await query.message.reply_text("🆕 أدخل اسم المستخدم للحساب:")

async def ichancy_deposit(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    account = get_ichancy_account(user_id)

    if not account or not account.get("username"):
        await query.edit_message_text("❌ يجب أن تنشئ حساب أولا")
        return

    context.user_data['ichancy_state'] = 'ichancy_deposit'

    await query.edit_message_text(
        "💰 **إيداع iChancy**\n\nأرسل المبلغ:",
        parse_mode="Markdown"
    )

async def handle_deposit_amount(update, context):
    user_id = str(update.effective_user.id)
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
        return

    account = get_ichancy_account(user_id)

    if amount <= 0:
        await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من 0")
        return

    if not account or not account.get("username"):
        await update.message.reply_text("❌ يجب أن تنشئ حساب أولا")
        return

    api = iChancyAPI()
    result = api.deposit_to_player_by_username(
        username=account["username"],
        amount=amount
    )

    if result['success']:
        await update.message.reply_text("✅ تم الشحن بنجاح")
    else:
        await update.message.reply_text(f"❌ فشل الشحن: {result.get('error', 'Unknown error')}")

async def ichancy_withdraw(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    account = get_ichancy_account(user_id)

    if not account or not account.get("username"):
        await query.edit_message_text("❌ يجب أن تنشئ حساب أولا")
        return

    await query.edit_message_text("💸 أرسل المبلغ الذي تريد سحبه:")
    context.user_data['ichancy_state'] = 'ichancy_withdraw'

async def handle_withdraw_amount(update, context):
    user_id = str(update.effective_user.id)
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
        return

    account = get_ichancy_account(user_id)

    api = iChancyAPI()
    result = api.withdraw_from_player_by_username(
        username=account["username"] if account else None,
        amount=amount
    )

    if result['success']:
        await update.message.reply_text("✅ تم السحب")
    else:
        await update.message.reply_text(f"❌ فشل السحب: {result.get('error', 'Unknown error')}")

async def ichancy_deposit_all(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    account = get_ichancy_account(user_id)

    if not account or not account.get("username"):
        await query.edit_message_text("❌ يجب أن تنشئ حساب أولا")
        return

    api = iChancyAPI()
    balance_result = api.get_player_balance_by_username(account["username"])

    if not balance_result['success']:
        await query.edit_message_text("❌ لا يمكن جلب الرصيد")
        return

    balance = balance_result.get('balance', 0)

    if balance <= 0:
        await query.edit_message_text("❌ لا يوجد رصيد")
        return

    result = api.withdraw_from_player_by_username(
        username=account["username"],
        amount=balance
    )

    if result['success']:
        await query.edit_message_text("✅ تم شحن كامل الرصيد")
    else:
        await query.edit_message_text(f"❌ فشل العملية: {result.get('error', 'Unknown error')}")

async def ichancy_balance(update, context):
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    account = get_ichancy_account(user_id)

    if not account or not account.get("username"):
        await query.edit_message_text("❌ يجب أن تنشئ حساب أولا")
        return

    api = iChancyAPI()
    balance_result = api.get_player_balance_by_username(account["username"])

    if balance_result['success']:
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

async def handle_ichancy_text(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get('ichancy_state')

    if state == "ichancy_wait_username":
        context.user_data['temp_username'] = text
        context.user_data['ichancy_state'] = "ichancy_wait_password"
        await update.message.reply_text("🔑 الآن أدخل كلمة مرور (8 أحرف على الأقل):")
        return

    if state == "ichancy_wait_password":
        if len(text) < 8:
            await update.message.reply_text("❌ كلمة المرور قصيرة، يجب أن تكون 8 أحرف على الأقل")
            return

        username = context.user_data.get("temp_username")
        password = text
        email = f"{user_id}@bot.com"

        api = iChancyAPI()
        res = api.register_player(
            username=username,
            password=password,
            email=email
        )

        if res and res.get("success"):
            player_id = res.get('player_id')
            if not player_id:
                player_id = api.get_player_id_by_username(username)

            context.user_data['ichancy_account'] = username
            context.user_data['ichancy_password'] = password
            context.user_data['ichancy_player_id'] = player_id

            try:
                supa.upsert_ichancy_details(
                    telegram_id=user_id,
                    username=username,
                    email=email,
                    password=password,
                    player_id=player_id or "0"
                )
            except Exception as e:
                logger.warning(f"Could not persist ichancy details to Supabase: {e}")

            context.user_data['ichancy_state'] = None
            context.user_data.pop('temp_username', None)

            await update.message.reply_text("✅ تم إنشاء الحساب بنجاح")
            await update.message.reply_text(
                "🎮 القائمة:",
                reply_markup=get_ichancy_keyboard(user_id)
            )
        else:
            error_msg = res.get('error', 'Unknown error') if res else 'Registration failed'
            await update.message.reply_text(f"❌ فشل: {error_msg}")

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
        reply_markup=get_ichancy_keyboard(telegram_id)
    )
