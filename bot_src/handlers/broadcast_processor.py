"""
🔥 معالج الرسائل الجماعية - يقوم بإرسال الرسائل المعلقة للمستخدمين
"""
import asyncio
import Logger
from telegram import Bot
from config.telegram import TOKEN
from supabase_integration import get_client

logger = Logger.getLogger()
bot = Bot(token=TOKEN) if TOKEN else None


async def process_pending_broadcasts():
    """معالجة الرسائل الجماعية المعلقة"""
    logger.info("📢 Broadcast processor checking for pending messages...")

    if not bot:
        logger.error("❌ Bot token not available")
        return

    if not TOKEN:
        logger.error("❌ TOKEN is empty!")
        return

    try:
        client = get_client()
        if not client:
            logger.error("❌ Supabase client not available")
            return

        logger.info("✅ Supabase client connected")

        # جلب الرسائل المعلقة
        res = client.table("pending_notifications") \
            .select("*") \
            .eq("status", "pending") \
            .limit(50) \
            .execute()

        notifications = res.data if res.data else []
        logger.info(f"📊 Found {len(notifications)} pending notifications")

        if not notifications:
            return

        for notif in notifications:
            telegram_id = notif.get("telegram_id")
            message = notif.get("message")
            notif_id = notif.get("id")

            if not telegram_id or not message:
                continue

            try:
                logger.info(f"Attempting to send notification to {telegram_id}: {message[:50]}...")
                
                # إرسال الرسالة للمستخدم
                await bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode="Markdown"
                )

                logger.info(f"Message sent successfully to {telegram_id}")

                # تحديث حالة الرسالة إلى "sent"
                update_result = client.table("pending_notifications") \
                    .update({
                        "status": "sent",
                        "sent_at": "now()"
                    }) \
                    .eq("id", notif_id) \
                    .execute()

                logger.info(f"Notification status updated to 'sent' for ID {notif_id}")

                # تأخير بسيط لتجنب rate limit
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to send notification to {telegram_id}: {e}")
                logger.error(f"Error details: {str(e)}")

                # تحديث حالة الرسالة إلى "failed"
                try:
                    client.table("pending_notifications") \
                        .update({
                            "status": "failed",
                            "error_message": str(e)
                        }) \
                        .eq("id", notif_id) \
                        .execute()
                    logger.info(f"Notification status updated to 'failed' for ID {notif_id}")
                except update_error:
                    logger.error(f"Failed to update notification status: {update_error}")

    except Exception as e:
        logger.error(f"Error processing pending broadcasts: {e}")


async def start_broadcast_processor():
    """بدء معالج الرسائل الجماعية في الخلفية"""
    logger.info("Starting broadcast processor...")

    while True:
        try:
            await process_pending_broadcasts()
        except Exception as e:
            logger.error(f"Broadcast processor error: {e}")

        # انتظر 10 ثواني قبل الفحص التالي
        await asyncio.sleep(10)
