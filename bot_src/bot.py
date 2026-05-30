import Logger
import logging
import config.telegram
import handlers.ichancy
import handlers.wheel_handler
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
from telegram.request import HTTPXRequest
import sys
import os
import asyncio
from datetime import datetime
import pytz
import urllib.request
import socket

from supabase import create_client
import supabase_integration as supa

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_KEY else None
print("SUPABASE URL:", SUPABASE_URL)
print("SUPABASE KEY:", "OK" if SUPABASE_KEY else "MISSING")

exchange_rate_cache = 15000
def load_exchange_rate():
    global exchange_rate_cache
    try:
        from database.supabase_client import get_setting
        rate = get_setting("usd_rate")
        if rate:
            exchange_rate_cache = float(rate)
            print("💱 Initial rate:", exchange_rate_cache)
    except Exception as e:
        print("Error loading exchange rate:", e)

def init_exchange_rate_realtime():
    import threading
    import time
    def poll_rate():
        global exchange_rate_cache
        while True:
            try:
                from database.supabase_client import get_setting
                rate = get_setting("usd_rate")
                if rate:
                    new_rate = float(rate)
                    if new_rate != exchange_rate_cache:
                        exchange_rate_cache = new_rate
                        print("⚡ RATE UPDATED:", exchange_rate_cache)
            except Exception as e:
                print("Rate poll error:", e)
            time.sleep(10)
    threading.Thread(target=poll_rate, daemon=True).start()
    
def log_to_db(event_type, message, telegram_id=None):
    try:
        from database.supabase_client import log_event
        log_event(event_type, message, telegram_id)
    except Exception as e:
        print("Log error:", e)

def save_transaction(user_id, t_type, amount, status="pending", note=""):
    try:
        from database.supabase_client import create_transaction
        create_transaction(user_id, t_type, amount, status=status, note=note)
    except Exception as e:
        print("Transaction error:", e)

def save_user(user):
    try:
        from database.supabase_client import upsert_user
        upsert_user(user.id, user.username, user.first_name)
    except Exception as e:
        print("Save user error:", e)

logger = Logger.getLogger()
DAMASCUS_TZ = pytz.timezone('Asia/Damascus')

def get_damascus_time():
    return datetime.now(DAMASCUS_TZ)

async def error_handler(update, context):
    print(f"Exception: {context.error}")
    log_to_db("error", str(context.error))

async def validate_real_transaction(transaction_data):
    try:
        if not transaction_data or 'value' not in transaction_data:
            return False, "بيانات المعاملة غير صالحة"
        value = transaction_data['value']
        if not isinstance(value, (int, float)) or value <= 0:
            return False, "القيمة غير صالحة"
        return True, "OK"
    except Exception as e:
        return False, str(e)

async def log_incoming_message(update, context):
    try:
        if update.message and update.message.text:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name or str(user_id)
            save_user(update.effective_user)
            from database.supabase_client import save_message, log_event
            save_message(user_id, username, update.message.text, "incoming")
            log_event("message_received", f"Message from {username}", user_id)
    except Exception as e:
        print("log_incoming_message error:", e)

async def real_time_monitoring():
    while True:
        try:
            current_time = get_damascus_time()
            log_to_db("system", f"Bot running {current_time}")
            try:
                socket.setdefaulttimeout(5)
                urllib.request.urlopen('https://api.telegram.org', timeout=5)
            except:
                log_to_db("warning", "Internet issue")
            await asyncio.sleep(300)
        except Exception as e:
            log_to_db("error", str(e))
            await asyncio.sleep(60)

notification_application = None

async def notification_polling():
    global notification_application
    await asyncio.sleep(5)
    while True:
        try:
            if notification_application:
                from database.supabase_client import supabase_client
                result = supabase_client.client.table("notifications") \
                    .select("*") \
                    .eq("is_sent", False) \
                    .order("created_at", desc=True) \
                    .limit(10) \
                    .execute()
                notifications = result.data or []
                for notif in notifications:
                    try:
                        telegram_id = notif.get("telegram_id")
                        message = notif.get("message")
                        notif_id = notif.get("id")
                        await notification_application.bot.send_message(
                            chat_id=telegram_id, text=message, parse_mode="HTML"
                        )
                        supabase_client.client.table("notifications") \
                            .update({"is_sent": True, "sent_at": datetime.now(timezone.utc).isoformat()}) \
                            .eq("id", notif_id) \
                            .execute()
                        log_to_db("notification_sent", f"Sent to {telegram_id}", telegram_id)
                    except Exception as e:
                        error_msg = str(e)
                        supabase_client.client.table("notifications") \
                            .update({"is_sent": True, "error": error_msg, "sent_at": datetime.now(timezone.utc).isoformat()}) \
                            .eq("id", notif_id) \
                            .execute()
            await asyncio.sleep(5)
        except Exception as e:
            log_to_db("notification_polling_error", str(e))
            await asyncio.sleep(10)

def main() -> None:
    try:
        if not config.telegram.TOKEN:
            print("Invalid token")
            exit(1)
        print("Bot starting...")
    except Exception as e:
        print(e)
        exit(1)

    try:
        import handlers.createAccount
        import handlers.error
        import handlers.button
        import handlers.ichancy_advanced
        import handlers.sendGifts
        import handlers.reseiveGifts
        import handlers.gift_code
        import handlers.command.start
        import handlers.command.balance
        import handlers.adminMessage
        import handlers.deposit
        import handlers.depositAccount
        import handlers.withdrawalAccount
        import handlers.withdrawal_conversation
        import handlers.admin_handler
        import handlers.bot_status
        import handlers.support_system

        request = HTTPXRequest()
        application = Application.builder() \
            .token(config.telegram.TOKEN) \
            .request(request) \
            .build()

        global notification_application
        notification_application = application

        from handlers.broadcast_processor import set_bot
        set_bot(application.bot)

        # حماية حالة البوت (الصيانة) - الأولوية القصوى
        application.add_handler(
            CallbackQueryHandler(handlers.bot_status.bot_status_callback_guard),
            group=-1,
        )
        application.add_handler(
            MessageHandler(filters.ALL, handlers.bot_status.bot_status_message_guard),
            group=-1,
        )

        # أوامر /start /balance /admin /cancel
        application.add_handler(CommandHandler('start', handlers.command.start.start), group=0)
        application.add_handler(CommandHandler('balance', handlers.command.balance.balance), group=0)
        application.add_handler(CommandHandler('admin', handlers.admin_handler.admin_command), group=0)

        async def cancel_all(update, context):
            await update.message.reply_text("✅ تم إنهاء العملية الحالية")
            await handlers.command.start.start(update, context)
            return ConversationHandler.END

        application.add_handler(CommandHandler('cancel', cancel_all), group=0)

        # محادثات (ConversationHandlers) - المجموعة 1
        application.add_handler(handlers.createAccount.conversationHandler(), group=1)
        application.add_handler(handlers.sendGifts.conversationHandler(), group=1)
        application.add_handler(handlers.reseiveGifts.conversationHandler(), group=1)
        application.add_handler(handlers.gift_code.conversationHandler(), group=1)
        application.add_handler(handlers.depositAccount.conversationHandler(), group=1)
        application.add_handler(handlers.withdrawalAccount.conversationHandler(), group=1)
        application.add_handler(handlers.adminMessage.conversationHandler(), group=1)
        application.add_handler(handlers.deposit.conversationHandler(), group=1)
        application.add_handler(handlers.withdrawal_conversation.conversationHandler(), group=1)
        # تسجيل ConversationHandler الخاص بنظام الدعم
        try:
            application.add_handler(handlers.support_system.SupportSystem.get_conversation_handler(), group=1)
        except Exception as e:
            print(f"Warning: Could not register support conversation handler: {e}")

        # معالجات الرسائل النصية - المجموعة 2
        # معالج إدخال المبالغ المتقدم لـ iChancy + معالج إنشاء الحساب من ichancy.py
        async def handle_text_routing(update, context):
            """توجيه الرسائل النصية حسب الحالة"""
            # التحقق من حالة إنشاء حساب ichancy
            ichancy_state = context.user_data.get('ichancy_state')
            if ichancy_state:
                await handlers.ichancy.handle_ichancy_text(update, context)
                return

            # التحقق من حالة إيداع/سحب ichancy المتقدم
            if context.user_data.get('ichancy_deposit') or context.user_data.get('ichancy_withdraw'):
                await handlers.ichancy_advanced.handle_ichancy_amount_input(update, context)
                return

        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_routing), group=2
        )

        # WebApp data handler
        application.add_handler(
            MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handlers.wheel_handler.handle_web_app_data), group=2
        )

        # معالج أزرار iChancy المباشر
        application.add_handler(
            CallbackQueryHandler(handlers.ichancy.handle_ichancy, pattern="^ichancy$"), group=3
        )

        # معالج الأزرار العام (يحوي admin_panel وكل شيء)
        application.add_handler(
            CallbackQueryHandler(handlers.button.button), group=3
        )

        # تسجيل الرسائل الواردة - المجموعة 4 (أخيراً)
        application.add_handler(
            MessageHandler(filters.TEXT, log_incoming_message), group=4
        )

        async def start_background_tasks(app):
            log_to_db("system", "Bot started successfully")
            load_exchange_rate()
            init_exchange_rate_realtime()
            asyncio.create_task(real_time_monitoring())
            asyncio.create_task(notification_polling())
            from handlers.broadcast_processor import start_broadcast_processor
            asyncio.create_task(start_broadcast_processor())

        application.post_init = start_background_tasks

        if os.getenv("RAILWAY_ENVIRONMENT") == "production":
            webhook_url = config.telegram.WEBHOOK_URL
            print(f"Starting bot in webhook mode: {webhook_url}")
            application.run_webhook(
                listen="0.0.0.0",
                port=config.telegram.PORT,
                url_path="webhook",
                webhook_url=webhook_url,
                drop_pending_updates=True
            )
        else:
            print("Starting bot in polling mode (development)")
            application.run_polling()

    except Exception as e:
        log_to_db("fatal", str(e))
        print("FATAL ERROR:", e)

if __name__ == '__main__':
    main()
