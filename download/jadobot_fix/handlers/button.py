import Logger
logger = Logger.getLogger()

# استيرادات مطلقة لكل الوحدات التي سنحتاجها
import handlers.checkStatus
import handlers.ichancy
import handlers.ichancy_advanced
import handlers.backToMenu
import handlers.help
import handlers.withdrawal
import handlers.deposit
import handlers.withdrawal_conversation
import handlers.conditions
import handlers.problemInBot
import handlers.problemInWebsite
import handlers.contactUs
import handlers.guidesHandlers.guides
import handlers.guidesHandlers.guidesWhatIchancy
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
import handlers.support_system
import handlers.analytics_handler
import handlers.backup_system
import handlers.maintenance_scheduler
import handlers.monitoring_system
import handlers.notification_system
import handlers.log
import handlers.wheel_handler  # ← تم النقل من داخل الدالة إلى هنا لحل مشكلة UnboundLocalError

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

    # ========================================
    # التحقق من الاشتراك بالقناة
    # ========================================
    if data == "check_sub":
        try:
            member = await context.bot.get_chat_member(
                chat_id="@jado_ichancy",
                user_id=user_id
            )
            if member.status in ["member", "administrator", "creator"]:
                await query.answer("✅ تم التحقق من الاشتراك، اضغط /start", show_alert=True)
            else:
                await query.answer("❌ لم تشترك بعد", show_alert=True)
        except Exception:
            await query.answer("⚠️ خطأ في التحقق", show_alert=True)
        return

    # ========================================
    # الموافقة / رفض الشروط
    # ========================================
    elif data == "agree":
        try:
            supa.upsert_user(
                telegram_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name or "",
                last_name=update.effective_user.last_name or ""
            )
            await query.answer("✅ تم قبول الشروط", show_alert=False)
            await query.message.edit_text("✅ تم قبول الشروط، اضغط /start للمتابعة")
        except Exception as e:
            print(f"Error in terms approval: {e}")
            await query.answer("❌ حدث خطأ، يرجى المحاولة مرة أخرى", show_alert=True)
        return

    elif data == "reject":
        await query.answer()
        await query.message.edit_text("❌ لا يمكنك استخدام البوت بدون الموافقة")
        return

    # ========================================
    # الشروحات
    # ========================================
    elif 'guide' in data:
        await query.answer()
        await guidesButton(update, context, query)
        return

    # ========================================
    # نظام الإحالات - يشمل كل الأزرار الفرعية
    # ========================================
    elif data == 'referral' or data.startswith('referral_') or \
         data in ('my_referrals', 'share_referral', 'copy_referral_link',
                  'referral_image', 'referral_text', 'gift_system'):
        await handlers.referral_handler.ReferralHandler.handle_referral_callback(update, context)
        return

    # ========================================
    # الإيداع
    # ========================================
    elif data == 'deposit':
        await query.answer()
        await handlers.deposit.handle_deposit(update, context)
        return

    # ========================================
    # الجاكبوت والألعاب والبونصات والعروض
    # ========================================
    elif data in ['jackpot', 'casino_games', 'sports_betting', 'betting_history',
                  'promotions', 'vip_program', 'live_support', 'open_ichancy'] or \
            data.startswith(('jackpot_', 'casino_', 'sports_', 'vip_', 'gaming_')):
        await handlers.gaming_handler.GamingHandler.handle_gaming_menu_callback(update, context)
        return

    # ========================================
    # السجل
    # ========================================
    elif data == 'log' or data.startswith('log_'):
        await handlers.log.LogHandler.handle_log_callback(update, context)
        return

    # ========================================
    # نظام الدعم والتواصل - يشمل كل الأزرار الفرعية
    # ========================================
    elif data in ('contact_us', 'contact', 'support_info', 'faq', 'message_admin',
                  'faq_menu', 'tech_support', 'direct_contact', 'problem_solved',
                  'send_to_admin') or \
         data.startswith('faq_') or data.startswith('support_'):
        await handlers.support_system.SupportSystem.handle_support_callback(update, context, data)
        return

    # ========================================
    # التحليلات (غير الأدمن)
    # ========================================
    elif data.startswith('analytics_') and not data.startswith('admin_analytics_'):
        await query.answer()
        await handlers.analytics_handler.AnalyticsHandler.handle_analytics_callback(update, context)
        return

    # ========================================
    # فحص الحالة
    # ========================================
    elif data == 'check_status':
        await query.answer()
        await handlers.checkStatus.handle_check_status(query, str(user_id))
        return

    # ========================================
    # المساعدة
    # ========================================
    elif data == 'help':
        await query.answer()
        await handlers.help.handle_help(query)
        return

    # ========================================
    # العودة للقائمة الرئيسية
    # ========================================
    elif data == 'back_to_menu':
        await query.answer()
        await handlers.backToMenu.handle_back_to_menu(query, username)
        return

    # ========================================
    # عجلة الحظ
    # ========================================
    elif data == 'spin_wheel':
        await query.answer()
        # ← تم نقل الاستيراد إلى أعلى الملف لحل مشكلة UnboundLocalError
        await handlers.wheel_handler.handle_spin_wheel(update, context)
        return

    # ========================================
    # نظام iChancy
    # ========================================
    elif data == 'ichancy':
        await handlers.ichancy.handle_ichancy(update, context)
        return

    elif data == 'ichancy_create_account':
        # لا نعالج هذا هنا - دع ConversationHandler في createAccount.py يلتقطه
        # ولكن إذا وصلنا هنا فالمحادثة لم تلتقطه، لذلك نعالجه يدوياً
        await handlers.ichancy.ichancy_create(update, context)
        return

    elif data == 'ichancy_account_info':
        await handlers.ichancy_advanced.ichancy_account_info(update, context)
        return

    elif data == 'ichancy_deposit_adv':
        await handlers.ichancy_advanced.ichancy_deposit_advanced(update, context)
        return

    elif data == 'ichancy_withdraw_adv':
        await handlers.ichancy_advanced.ichancy_withdraw_advanced(update, context)
        return

    elif data == 'ichancy_deposit_all_adv':
        await handlers.ichancy_advanced.ichancy_deposit_all_advanced(update, context)
        return

    elif data == 'ichancy_transactions':
        await handlers.ichancy_advanced.ichancy_transactions(update, context)
        return

    elif data == 'back_to_ichancy':
        await handlers.ichancy.handle_ichancy(update, context)
        return

    elif data == 'ichancy_delete_account':
        await handlers.ichancy.delete_account_handler(update, context)
        return

    elif data == 'ichancy_deposit':
        await handlers.ichancy.ichancy_deposit(update, context)
        return

    elif data == 'ichancy_withdraw':
        await handlers.ichancy.ichancy_withdraw(update, context)
        return

    elif data == 'ichancy_balance':
        await handlers.ichancy.ichancy_balance(update, context)
        return

    # ========================================
    # سحب / إيداع قديم
    # ========================================
    elif data == 'withdrawal_old':
        await query.answer()
        await handlers.withdrawal.handle_withdrawal(query, str(user_id))
        return

    elif data == 'deposit_old':
        await query.answer()
        await handlers.deposit.handle_deposit(query, str(user_id))
        return

    # ========================================
    # الشروط والأحكام
    # ========================================
    elif data == 'terms_and_conditions':
        await query.answer()
        await handlers.conditions.handle_terms_and_conditions(query, mode="menu")
        return

    # ========================================
    # مشكلة في البوت / الموقع
    # ========================================
    elif data == 'problem_in_bot':
        await query.answer()
        await handlers.problemInBot.handle_problem_in_bot(query)
        return

    elif data == 'problem_in_website':
        await query.answer()
        await handlers.problemInWebsite.handle_problem_in_website(query)
        return

    # ========================================
    # المعاملات - موافقة / رفض
    # ========================================
    elif data.startswith('approve_'):
        await query.answer()
        parts = data.split('_')
        if len(parts) >= 3:
            transaction_type = parts[1]
            transaction_id = '_'.join(parts[2:])
            await handlers.transactions.approve_transaction(query, transaction_id, transaction_type)
        return

    elif data.startswith('reject_'):
        await query.answer()
        parts = data.split('_')
        if len(parts) >= 3:
            transaction_type = parts[1]
            transaction_id = '_'.join(parts[2:])
            await handlers.transactions.reject_transaction(query, transaction_id, transaction_type)
        return

    # ========================================
    # لوحة الإدمن - تشمل كل الأزرار الفرعية بما فيها analytics
    # ========================================
    elif data == 'admin_panel':
        await handlers.admin_handler.AdminHandler.admin_panel(update, context)
        return

    elif data.startswith('admin_'):
        # جميع أزرار الأدمن بما فيها admin_analytics_* تذهب لنفس المعالج
        await handlers.admin_handler.AdminHandler.handle_admin_callback(update, context)
        return

    # ========================================
    # أنظمة الصيانة والمراقبة والنسخ الاحتياطي والإشعارات
    # ========================================
    elif data.startswith('maintenance_'):
        await handlers.maintenance_scheduler.MaintenanceScheduler.handle_maintenance_callback(update, context)
        return

    elif data.startswith('monitor_'):
        await handlers.monitoring_system.MonitoringSystem.handle_monitoring_callback(update, context)
        return

    elif data.startswith('backup_'):
        await handlers.backup_system.BackupSystem.handle_backup_callback(update, context)
        return

    elif data.startswith('notification_'):
        await handlers.notification_system.NotificationSystem.handle_notification_callback(update, context)
        return

    # ========================================
    # زر غير معروف
    # ========================================
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
