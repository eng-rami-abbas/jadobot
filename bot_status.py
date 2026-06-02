"""
Check bot pause status from Supabase app_settings (control panel).

When the bot is paused:
  - ALL callbacks are blocked (including admin buttons - admin must use /admin to unpause)
  - ALL messages are blocked (including /start, /cancel, /balance)
  - The user sees the saved maintenance message as a regular text message
"""
import time
import logging
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop

import supabase_integration as supa

logger = logging.getLogger(__name__)

_cache = {"status": "active", "message": "", "expires": 0.0}
CACHE_TTL_SEC = 8

# Callbacks that are ALWAYS allowed even when bot is paused
# Only subscription check and terms-related callbacks
ALWAYS_ALLOWED_CALLBACKS = {
    "check_sub",
}


def _refresh_cache():
    now = time.time()
    if now < _cache["expires"]:
        return
    try:
        client = supa.get_client()
        res = client.table("app_settings").select("key,value").in_(
            "key", ["bot_status", "bot_stop_message"]
        ).execute()
        settings = {row["key"]: row["value"] for row in (res.data or [])}
        _cache["status"] = settings.get("bot_status", "active")
        _cache["message"] = settings.get(
            "bot_stop_message",
            "⏸️ البوت متوقف مؤقتاً للصيانة. يرجى المحاولة لاحقاً.",
        )
    except Exception as e:
        logger.error(f"bot_status cache refresh error: {e}")
    _cache["expires"] = now + CACHE_TTL_SEC


def is_bot_paused() -> bool:
    _refresh_cache()
    return _cache["status"] == "paused"


def get_maintenance_message() -> str:
    _refresh_cache()
    return _cache["message"]


def _is_admin(user_id) -> bool:
    """Check if user is admin."""
    try:
        import config.telegram
        admin_id = str(config.telegram.ADMIN_TELEGRAM_ID)
        return str(user_id) == admin_id
    except Exception:
        return False


async def _reply_paused(update: Update):
    """Send the maintenance message as a regular text message."""
    text = get_maintenance_message()
    if update.callback_query:
        # Answer the callback query to remove the loading state
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        # Send maintenance message as a new regular message
        try:
            await update.callback_query.message.reply_text(text)
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text(text)


async def bot_status_callback_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guard for ALL callback queries. Blocks everything when bot is paused except admin callbacks."""
    if not update.callback_query:
        return
    data = update.callback_query.data or ""

    # Always allowed callbacks (subscription check only)
    if data in ALWAYS_ALLOWED_CALLBACKS:
        return

    # Admin callbacks are always allowed (admin panel, bot status management)
    if data.startswith("admin_"):
        return

    # Block all other callbacks when bot is paused
    if is_bot_paused():
        await _reply_paused(update)
        raise ApplicationHandlerStop()


async def bot_status_message_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guard for ALL messages. Blocks EVERYTHING when bot is paused including /start, /cancel, /balance."""
    if not update.message:
        return

    # Admin users are always allowed
    if _is_admin(update.effective_user.id):
        return

    # When bot is paused, block ALL messages including commands
    if is_bot_paused():
        await _reply_paused(update)
        raise ApplicationHandlerStop()
