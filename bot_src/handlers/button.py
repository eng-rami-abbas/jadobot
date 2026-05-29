import Logger
logger = Logger.getLogger()

# استيرادات مباشرة من داخل الحزمة (نسبية)
from . import checkStatus, ichancy, ichancy_advanced
from . import backToMenu, help, withdrawal, deposit, withdrawal_conversation, conditions
from . import problemInBot, problemInWebsite, contactUs
from . import syriatel_cash_deposit
from . import transactions
from .admin_handler import AdminHandler
from .referral_handler import ReferralHandler
from .referral_system import *  # إن احتجت دوال محددة فاستوردها مباشرة
from .gaming_handler import GamingHandler
from .support_system import SupportSystem
from .analytics_handler import AnalyticsHandler
from .backup_system import BackupSystem
from .maintenance_scheduler import MaintenanceScheduler
from .monitoring_system import MonitoringSystem
from .notification_system import NotificationSystem
from .log import LogHandler
from .guidesHandlers.guides import handle_guides
from .guidesHandlers.guidesWhatIchancy import handle_guides_what_is_ichancy
from .guidesHandlers.guidesHowToCreateNewAccount import handle_guides_how_to_create_new_account
from .guidesHandlers.guidesHowDepositTelegramAccount import handle_guides_how_deposit_telegram_account
from .guidesHandlers.guidesHowWithdrawTelegramAccount import handle_guides_how_withdraw_telegram_account
from .guidesHandlers.guidesHowDepositIchancyAccount import handle_guides_how_deposit_ichancy_account
from .guidesHandlers.guidesHowWithdrawIchancyAccount import handle_guides_how_withdraw_ichancy_account
from .transactions import approve_transaction, reject_transaction

import store
import supabase_integration as supa

from config.telegram import Update
from telegram.ext import ContextTypes


async def is_blocked(update, context):
    user_id = update.effective_user.id
    try:
        if supa.is_user_blocked(user_id):
            return "blocked"
    except Exception as e:
        logger.error(f"Supabase upsert error: {e}")
    try:
        member = await context.bot.get_chat_member(
            chat_id="@jado_ichancy",
            user_id=user_id
        )
        if member.status not in ["member", "administrator", "creator"]:
            return "channel"
    except Exception:
        return "channel"
    return None


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    username = update.effective_user.username or "مستخدم"
    data = query.data

    try:
        supa.upsert_user(
            telegram_id=user_id,
            username=username,
            first_name=update.effective_user.first_name or "",
            last_name=update.effective_user.last_name or ""
        )
    except Exception:
        pass

    ALWAYS_ALLOWED = {
        "check_sub",
        "agree",
        "reject",
        "terms_and_conditions"
    }

    if data not in ALWAYS_ALLOWED:
        block = await is_blocked(update, context)
        if block == "blocked":
            await query.answer("🚫 تم حظر حسابك. تواصل مع الدعم.", show_alert=True)
            return
        if block == "terms":
            await query.answer("⚠️ يجب الموافقة على الشروط أولاً", show_alert=True)
            await conditions.handle_terms_and_conditions(query, mode="start")
            return
        if block == "channel":
            await query.answer("❌ يجب الاشتراك بالقناة أولاً", show_alert=True)
            return

    if data == "check_sub":
        try:
            member = await context.bot.get_chat_member(
                chat_id="@jado_ichancy",
                user_id=user_id
            )
            if member.status in ["member", "administrator", "creator"]:
                await query.message.reply_text("✅ تم التحقق من الاشتراك، اضغط /start")
            else:
                await query.answer("❌ لم تشترك بعد", show_alert=True)
        except Exception:
            await query.answer("⚠️ خطأ في التحقق", show_alert=True)

    elif data == "agree":
        try:
            supa.upsert_user(
                telegram_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name or "",
                last_name=update.effective_user.last_name or ""
            )
            await query.message.edit_text("✅ تم قبول الشروط، اضغط /start للمتابعة")
        except Exception as e:
            print(f"Error in terms approval: {e}")
            await query.message.edit_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        return

    elif data == "reject":
        await query.message.edit_text("❌ لا يمكنك استخدام البوت بدون الموافقة")
        return

    if 'guide' in data:
        await guidesButton(update, context, query)

    elif data == 'referral' or data.startswith('referral_'):
        await ReferralHandler.handle_referral_callback(update, context)

    elif data == 'deposit':
        await deposit.handle_deposit(update, context)

    elif data in ['jackpot', 'casino_games', 'sports_betting', 'betting_history',
                  'promotions', 'vip_program', 'live_support', 'open_ichancy'] or \
            data.startswith(('jackpot_', 'casino_', 'sports_', 'vip_', 'gaming_')):
        await GamingHandler.handle_gaming_menu_callback(update, context)

    elif data == 'log' or data.startswith('log_'):
        await LogHandler.handle_log_callback(update, context)

    elif data in ['support_info', 'faq', 'message_admin', 'contact']:
        await SupportSystem.handle_support_callback(update, context, data)

    elif data.startswith('analytics_'):
        await AnalyticsHandler.handle_analytics_callback(update, context)

    elif data == 'check_status':
        await checkStatus.handle_check_status(query, str(user_id))

    elif data == 'help':
        await help.handle_help(query)

    elif data == 'back_to_menu':
        await backToMenu.handle_back_to_menu(query, username)

    elif data == 'spin_wheel':
        import handlers.wheel_handler
        await handlers.wheel_handler.handle_spin_wheel(update, context)

    elif data == 'ichancy':
        await ichancy.handle_ichancy(update, context)

    elif data == 'ichancy_create_account':
        await ichancy.ichancy_create(update, context)

    elif data == 'ichancy_account_info':
        await ichancy_advanced.ichancy_account_info(update, context)

    elif data == 'ichancy_deposit_adv':
        await ichancy_advanced.ichancy_deposit_advanced(update, context)

    elif data == 'ichancy_withdraw_adv':
        await ichancy_advanced.ichancy_withdraw_advanced(update, context)

    elif data == 'ichancy_deposit_all_adv':
        await ichancy_advanced.ichancy_deposit_all_advanced(update, context)

    elif data == 'ichancy_transactions':
        await ichancy_advanced.ichancy_transactions(update, context)

    elif data == 'back_to_ichancy':
        await ichancy.handle_ichancy(update, context)

    elif data == 'ichancy_delete_account':
        await ichancy.delete_account_handler(update, context)

    elif data == 'ichancy_deposit':
        await ichancy.ichancy_deposit(update, context)

    elif data == 'ichancy_withdraw':
        await ichancy.ichancy_withdraw(update, context)

    elif data == 'ichancy_balance':
        await ichancy.ichancy_balance(update, context)

    elif data == 'withdrawal_old':
        await withdrawal.handle_withdrawal(query, str(user_id))

    elif data == 'deposit_old':
        await deposit.handle_deposit(query, str(user_id))

    elif data == 'terms_and_conditions':
        await conditions.handle_terms_and_conditions(query, mode="menu")

    elif data == 'contact_us':
        await contactUs.handle_contact_us(query)

    elif data == 'problem_in_bot':
        await problemInBot.handle_problem_in_bot(query)

    elif data == 'problem_in_website':
        await problemInWebsite.handle_problem_in_website(query)

    elif data.startswith('approve_'):
        parts = data.split('_')
        if len(parts) >= 3:
            transaction_type = parts[1]
            transaction_id = '_'.join(parts[2:])
            await approve_transaction(query, transaction_id, transaction_type)

    elif data.startswith('reject_'):
        parts = data.split('_')
        if len(parts) >= 3:
            transaction_type = parts[1]
            transaction_id = '_'.join(parts[2:])
            await reject_transaction(query, transaction_id, transaction_type)

    elif data == 'admin_panel':
        await AdminHandler.admin_panel(update, context)
        return

    elif data.startswith('admin_'):
        if not (data.startswith('admin_approve_') or
                data.startswith('admin_reject_') or
                data.startswith('admin_analytics_')):
            await AdminHandler.handle_admin_callback(update, context)

    elif data.startswith('maintenance_'):
        await MaintenanceScheduler.handle_maintenance_callback(update, context)

    elif data.startswith('monitor_'):
        await MonitoringSystem.handle_monitoring_callback(update, context)

    elif data.startswith('backup_'):
        await BackupSystem.handle_backup_callback(update, context)

    elif data.startswith('notification_'):
        await NotificationSystem.handle_notification_callback(update, context)

    else:
        await query.answer(f"زر غير معروف: {data}", show_alert=True)


async def guidesButton(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    data = query.data
    if data == "guides":
        await handle_guides(query)
    elif data == "guides_what_is_ichancy":
        await handle_guides_what_is_ichancy(query)
    elif data == "guides_how_deposit_telegram_account":
        await handle_guides_how_deposit_telegram_account(query)
    elif data == "guides_how_to_create_new_account":
        await handle_guides_how_to_create_new_account(query)
    elif data == "guides_how_withdraw_telegram_account":
        await handle_guides_how_withdraw_telegram_account(query)
    elif data == "guides_how_deposit_ichancy_account":
        await handle_guides_how_deposit_ichancy_account(query)
    elif data == "guides_how_withdraw_ichancy_account":
        await handle_guides_how_withdraw_ichancy_account(query)
