import handlers.checkStatus, handlers.ichancy, handlers.ichancy_advanced
import handlers.backToMenu, handlers.help, handlers.withdrawal, handlers.deposit, handlers.withdrawal_conversation, handlers.conditions, handlers.problemInBot, handlers.problemInWebsite
import handlers.contactUs
import handlers.guidesHandlers.guides, handlers.guidesHandlers.guidesWhatIchancy
import handlers.guidesHandlers.guidesHowToCreateNewAccount
import handlers.guidesHandlers.guidesHowDepositTelegramAccount
import handlers.guidesHandlers.guidesHowWithdrawTelegramAccount
import handlers.guidesHandlers.guidesHowDepositIchancyAccount
import handlers.guidesHandlers.guidesHowWithdrawIchancyAccount
import handlers.syriatel_cash_deposit
import handlers.transactions
import handlers.admin_handler
import handlers.referral_handler
import handlers.referral_system
import handlers.gaming_handler
import store
import handlers.support_system
import handlers.analytics_handler
import handlers.backup_system
import handlers.maintenance_scheduler
import handlers.monitoring_system
import handlers.notification_system
import handlers.log 
import supabase_integration as supa

from config.telegram import Update
from telegram.ext import ContextTypes


async def is_blocked(update, context):
    user_id = update.effective_user.id
    try:
        if supa.is_user_blocked(user_id):
            return "blocked"
    except Exception:
        pass
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
            await handlers.conditions.handle_terms_and_conditions(query, mode="start")
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
        await handlers.referral_handler.ReferralHandler.handle_referral_callback(update, context)

    elif data == 'deposit':
        await handlers.deposit.handle_deposit(update, context)

    elif data in ['jackpot', 'casino_games', 'sports_betting', 'betting_history',
                  'promotions', 'vip_program', 'live_support', 'open_ichancy'] or \
         data.startswith(('jackpot_', 'casino_', 'sports_', 'vip_', 'gaming_')):
        await handlers.gaming_handler.GamingHandler.handle_gaming_menu_callback(update, context)

    elif data == 'log' or data.startswith('log_'):
        await handlers.log.LogHandler.handle_log_callback(update, context)

    elif data in ['support_info', 'faq', 'message_admin', 'contact']:
        await handlers.support_system.SupportSystem.handle_support_callback(update, context, data)

    elif data.startswith('analytics_'):
        await handlers.analytics_handler.AnalyticsHandler.handle_analytics_callback(update, context)

    elif data == 'check_status':
        await handlers.checkStatus.handle_check_status(query, str(user_id))

    elif data == 'help':
        await handlers.help.handle_help(query)

    elif data == 'back_to_menu':
        await handlers.backToMenu.handle_back_to_menu(query, username)

    elif data == 'spin_wheel':
        import handlers.wheel_handler
        await handlers.wheel_handler.handle_spin_wheel(update, context)

    elif data == 'ichancy':
        await handlers.ichancy.handle_ichancy(update, context)

    elif data == 'ichancy_create_account':
        await handlers.ichancy.ichancy_create(update, context)

    elif data == 'ichancy_account_info':
        await handlers.ichancy_advanced.ichancy_account_info(update, context)

    elif data == 'ichancy_deposit_adv':
        await handlers.ichancy_advanced.ichancy_deposit_advanced(update, context)

    elif data == 'ichancy_withdraw_adv':
        await handlers.ichancy_advanced.ichancy_withdraw_advanced(update, context)

    elif data == 'ichancy_deposit_all_adv':
        await handlers.ichancy_advanced.ichancy_deposit_all_advanced(update, context)

    elif data == 'ichancy_transactions':
        await handlers.ichancy_advanced.ichancy_transactions(update, context)

    elif data == 'back_to_ichancy':
        await handlers.ichancy.handle_ichancy(update, context)

    elif data == 'ichancy_delete_account':
        await handlers.ichancy.delete_account_handler(update, context)

    elif data == 'ichancy_deposit':
        await handlers.ichancy.ichancy_deposit(update, context)

    elif data == 'ichancy_withdraw':
        await handlers.ichancy.ichancy_withdraw(update, context)

    elif data == 'ichancy_balance':
        await handlers.ichancy.ichancy_balance(update, context)

    elif data == 'withdrawal_old':
        await handlers.withdrawal.handle_withdrawal(query, str(user_id))

    elif data == 'deposit_old':
        await handlers.deposit.handle_deposit(query, str(user_id))

    elif data == 'terms_and_conditions':
        await handlers.conditions.handle_terms_and_conditions(query, mode="menu")

    elif data == 'contact_us':
        await handlers.contactUs.handle_contact_us(query)

    elif data == 'problem_in_bot':
        await handlers.problemInBot.handle_problem_in_bot(query)

    elif data == 'problem_in_website':
        await handlers.problemInWebsite.handle_problem_in_website(query)

    elif data.startswith('approve_'):
        parts = data.split('_')
        if len(parts) >= 3:
            transaction_type = parts[1]
            transaction_id = '_'.join(parts[2:])
            await handlers.transactions.approve_transaction(query, transaction_id, transaction_type)

    elif data.startswith('reject_'):
        parts = data.split('_')
        if len(parts) >= 3:
            transaction_type = parts[1]
            transaction_id = '_'.join(parts[2:])
            await handlers.transactions.reject_transaction(query, transaction_id, transaction_type)

    elif data.startswith('admin_'):
        await handlers.admin_handler.AdminHandler.handle_admin_callback(update, context)

    elif data.startswith('maintenance_'):
        await handlers.maintenance_scheduler.MaintenanceScheduler.handle_maintenance_callback(update, context)

    elif data.startswith('monitor_'):
        await handlers.monitoring_system.MonitoringSystem.handle_monitoring_callback(update, context)

    elif data.startswith('backup_'):
        await handlers.backup_system.BackupSystem.handle_backup_callback(update, context)

    elif data.startswith('notification_'):
        await handlers.notification_system.NotificationSystem.handle_notification_callback(update, context)

    else:
        await query.answer(f"زر غير معروف: {data}", show_alert=True)


async def guidesButton(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    data = query.data
    if data == "guides":
        await handlers.guidesHandlers.guides.handle_guides(query)
    elif data == "guides_what_is_ichancy":
        await handlers.guidesHandlers.guidesWhatIchancy.handle_guides_what_is_ichancy(query)
    elif data == "guides_how_deposit_telegram_account":
        await handlers.guidesHandlers.guidesHowDepositTelegramAccount.handle_guides_how_deposit_telegram_account(query)
    elif data == "guides_how_to_create_new_account":
        await handlers.guidesHandlers.guidesHowToCreateNewAccount.handle_guides_how_to_create_new_account(query)
    elif data == "guides_how_withdraw_telegram_account":
        await handlers.guidesHandlers.guidesHowWithdrawTelegramAccount.handle_guides_how_withdraw_telegram_account(query)
    elif data == "guides_how_deposit_ichancy_account":
        await handlers.guidesHandlers.guidesHowDepositIchancyAccount.handle_guides_how_deposit_ichancy_account(query)
    elif data == "guides_how_withdraw_ichancy_account":
        await handlers.guidesHandlers.guidesHowWithdrawIchancyAccount.handle_guides_how_withdraw_ichancy_account(query)
