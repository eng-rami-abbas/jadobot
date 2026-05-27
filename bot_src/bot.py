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

# =========================
# 🔥 SUPABASE INTEGRATION
# =========================
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

            time.sleep(10)  # كل 10 ثواني

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

# =========================
# ✅ NEW: SAVE USER FUNCTION
# =========================
def save_user(user):
    try:
        from database.supabase_client import upsert_user
        upsert_user(user.id, user.username, user.first_name)
    except Exception as e:
        print("Save user error:", e)

# =========================

logger = Logger.getLogger()

# =========================
# 🕒 Time Setup
# =========================
DAMASCUS_TZ = pytz.timezone('Asia/Damascus')

def get_damascus_time():
    return datetime.now(DAMASCUS_TZ)

# =========================
# ❌ ERROR HANDLER
# =========================
async def error_handler(update, context):
    print(f"Exception: {context.error}")
    log_to_db("error", str(context.error))

# =========================
# 🔥 VALIDATION
# =========================
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

# =========================
# 🔥 MONITORING
# =========================
async def log_incoming_message(update, context):
    try:
        if update.message and update.message.text:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name or str(user_id)

            print(f"[DEBUG] log_incoming_message: user={user_id}, text={update.message.text[:50]}...")

            # ✅ NEW: SAVE USER HERE
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


# =========================
# 🔥 NOTIFICATION SERVICE
# =========================
notification_application = None

async def notification_polling():
    """Poll for pending notifications and send them via Telegram."""
    global notification_application
    await asyncio.sleep(5)  # Wait for bot to initialize
    
    while True:
        try:
            if notification_application:
                from database.supabase_client import supabase_client
                # Get pending notifications
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
                            chat_id=telegram_id,
                            text=message,
                            parse_mode="HTML"
                        )
                        
                        # Mark as sent
                        supabase_client.client.table("notifications") \
                            .update({"is_sent": True, "sent_at": datetime.now(timezone.utc).isoformat()}) \
                            .eq("id", notif_id) \
                            .execute()
                        
                        log_to_db("notification_sent", f"Sent to {telegram_id}", telegram_id)
                        
                    except Exception as e:
                        error_msg = str(e)
                        log_to_db("notification_error", f"Failed to send to {telegram_id}: {error_msg}", telegram_id)
                        # Mark as sent with error
                        supabase_client.client.table("notifications") \
                            .update({"is_sent": True, "error": error_msg, "sent_at": datetime.now(timezone.utc).isoformat()}) \
                            .eq("id", notif_id) \
                            .execute()
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            log_to_db("notification_polling_error", str(e))
            await asyncio.sleep(10)

# =========================
# 🚀 MAIN BOT
# =========================
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
        import handlers.gift_code  # 🎁 استيراد معالج أكواد الهدايا
        import handlers.command.start
        import handlers.command.balance
        import handlers.adminMessage
        import handlers.deposit
        import handlers.depositAccount
        import handlers.withdrawalAccount
        import handlers.withdrawal_conversation
        import handlers.admin_handler
        import handlers.bot_status

        request = HTTPXRequest()

        application = Application.builder() \
            .token(config.telegram.TOKEN) \
            .request(request) \
            .build()

        # Set global notification application reference
        global notification_application
        notification_application = application

        from handlers.broadcast_processor import set_bot
        set_bot(application.bot)

        # Bot pause from control panel (app_settings.bot_status)
        application.add_handler(
            CallbackQueryHandler(handlers.bot_status.bot_status_callback_guard),
            group=-1,
        )
        application.add_handler(
            MessageHandler(filters.ALL, handlers.bot_status.bot_status_message_guard),
            group=-1,
        )

        # 🔥 أضف أوامر البوت أولاً بأولوية عالية (group=0) لتجنب التعارض مع ConversationHandler
        application.add_handler(CommandHandler('start', handlers.command.start.start), group=0)
        application.add_handler(CommandHandler('balance', handlers.command.balance.balance), group=0)
        application.add_handler(CommandHandler('admin', handlers.admin_handler.admin_command), group=0)

        # 🔥 معالج /cancel لإنهاء أي محادثة وعرض القائمة الرئيسية
        async def cancel_all(update, context):
            """Cancel any ongoing conversation and return to main menu"""
            await update.message.reply_text("✅ تم إنهاء العملية الحالية")
            # Return to main menu by calling start
            await handlers.command.start.start(update, context)
            return ConversationHandler.END

        application.add_handler(CommandHandler('cancel', cancel_all), group=0)

        # Conversation handlers (group=1 - أولوية أقل)
        application.add_handler(handlers.createAccount.conversationHandler(), group=1)
        application.add_handler(handlers.sendGifts.conversationHandler(), group=1)
        application.add_handler(handlers.reseiveGifts.conversationHandler(), group=1)
        application.add_handler(handlers.gift_code.conversationHandler(), group=1)  # 🎁 كود هدية
        application.add_handler(handlers.depositAccount.conversationHandler(), group=1)
        application.add_handler(handlers.withdrawalAccount.conversationHandler(), group=1)
        application.add_handler(handlers.adminMessage.conversationHandler(), group=1)
        application.add_handler(handlers.deposit.conversationHandler(), group=1)
        application.add_handler(handlers.withdrawal_conversation.conversationHandler(), group=1)
        application.add_handler(
            CallbackQueryHandler(handlers.ichancy.handle_ichancy, pattern="^ichancy$"), group=3
        )

        # 🔥 Web App data handler
        application.add_handler(
            MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handlers.wheel_handler.handle_web_app_data), group=2
        )

        # Handle advanced iChancy deposit/s withdraw text inputs before generic logging
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.ichancy_advanced.handle_ichancy_amount_input), group=2
        )

        # ======== 🟢 معالج زر لوحة الإدمن (أولوية أعلى من button العام) ========
        application.add_handler(
            CallbackQueryHandler(handlers.admin_handler.AdminHandler.admin_panel, pattern="^admin_panel$"),
            group=2
        )
        # =============================================================

        application.add_handler(
            CallbackQueryHandler(handlers.button.button), group=3
        )

        # Message logging - group=3 (بعد معالجات النص الخاصة بالمعاملات)
        application.add_handler(
            MessageHandler(filters.TEXT, log_incoming_message), group=3
        )

        # 🔥 post_init to start background tasks
        async def start_background_tasks(app):
            """Start background tasks after bot initialization"""
            log_to_db("system", "Bot started successfully")
            load_exchange_rate()
            init_exchange_rate_realtime()
            # Start background tasks
            asyncio.create_task(real_time_monitoring())
            asyncio.create_task(notification_polling())
            # 🔥 Broadcast processor
            from handlers.broadcast_processor import start_broadcast_processor
            asyncio.create_task(start_broadcast_processor())

        application.post_init = start_background_tasks

        # 🔥 WEBHOOK SETUP FOR RAILWAY
        if os.getenv("RAILWAY_ENVIRONMENT") == "production":
            # Production mode - use webhook
            webhook_url = config.telegram.WEBHOOK_URL
            print(f"Starting bot in webhook mode: {webhook_url}")
            
            # Set webhook and start server
            application.run_webhook(
                listen="0.0.0.0",
                port=config.telegram.PORT,
                url_path="webhook",
                webhook_url=webhook_url,
                drop_pending_updates=True
            )
        else:
            # Development mode - use polling
            print("Starting bot in polling mode (development)")
            application.run_polling()

    except Exception as e:
        log_to_db("fatal", str(e))
        print("FATAL ERROR:", e)


if __name__ == '__main__':
    main()
