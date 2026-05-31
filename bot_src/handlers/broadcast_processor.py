"""
معالج الإشعارات المعلقة — إرسال رسائل الموافقة/الرفض للمستخدمين
"""
import asyncio
import logging
from datetime import datetime, timezone

import Logger
from telegram import Bot
from telegram.error import BadRequest, Forbidden, TelegramError
from config.telegram import TOKEN
from supabase_integration import get_client

logger = Logger.getLogger()
logging.getLogger("httpx").setLevel(logging.WARNING)

_bot: Bot | None = None


def get_bot() -> Bot | None:
    global _bot
    if _bot is None and TOKEN:
        _bot = Bot(token=TOKEN)
    return _bot


def set_bot(bot: Bot):
    """Use the running application bot (preferred on Railway/webhook)."""
    global _bot
    _bot = bot


async def _send_notification(bot: Bot, telegram_id: int, message: str):
    """Send without Markdown to avoid parse errors on user-facing templates."""
    try:
        await bot.send_message(chat_id=telegram_id, text=message)
    except BadRequest:
        # Fallback: strip common markdown chars
        plain = (
            message.replace("*", "")
            .replace("_", "")
            .replace("`", "")
        )
        await bot.send_message(chat_id=telegram_id, text=plain)


async def process_pending_broadcasts():
    bot = get_bot()
    if not bot:
        logger.error("Broadcast processor: bot token not available")
        return

    try:
        client = get_client()
        res = client.table("pending_notifications") \
            .select("*") \
            .eq("status", "pending") \
            .order("created_at") \
            .limit(50) \
            .execute()

        notifications = res.data or []
        if not notifications:
            return

        logger.info(f"Processing {len(notifications)} pending notification(s)")

        for notif in notifications:
            notif_id = notif.get("id")
            raw_tid = notif.get("telegram_id")
            message = notif.get("message")

            if not raw_tid or not message:
                continue

            try:
                telegram_id = int(raw_tid)
            except (TypeError, ValueError):
                logger.error(f"Invalid telegram_id in notification {notif_id}: {raw_tid}")
                continue

            try:
                await _send_notification(bot, telegram_id, message)

                client.table("pending_notifications").update({
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": None,
                }).eq("id", notif_id).execute()

                logger.info(f"Notification sent to {telegram_id}")

            except Forbidden as e:
                err = f"User blocked bot: {e}"
                logger.warning(err)
                client.table("pending_notifications").update({
                    "status": "failed",
                    "error_message": err,
                }).eq("id", notif_id).execute()

            except TelegramError as e:
                err = str(e)
                logger.error(f"Failed to send to {telegram_id}: {err}")
                client.table("pending_notifications").update({
                    "status": "failed",
                    "error_message": err,
                }).eq("id", notif_id).execute()

            await asyncio.sleep(0.15)

    except Exception as e:
        logger.error(f"Error processing pending broadcasts: {e}")


async def start_broadcast_processor():
    logger.info("Broadcast processor started")
    while True:
        try:
            await process_pending_broadcasts()
        except Exception as e:
            logger.error(f"Broadcast processor loop error: {e}")
        await asyncio.sleep(8)
