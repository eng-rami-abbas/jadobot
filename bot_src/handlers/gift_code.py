# =========================
# 🎁 نظام أكواد الهدايا
# =========================

from telegram.ext import ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from telegram import CallbackQuery
import supabase_integration as supa
import Logger
from datetime import datetime, timezone

logger = Logger.getLogger()

# حالات المحادثة
ENTER_CODE = 1

# تخزين مؤقت للمستخدمين
user_states = {}


async def handle_gift_code(update, context):
    """بدء محادثة كود الهدية"""
    user_id = update.effective_user.id

    logger.info(f"[GiftCode] User {user_id} started gift code flow")

    # التحقق إذا كان الاستدعاء من callback أو message
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "🎁 **أدخل كود الهدية**\n\n"
            "💡 الكود يستخدم مرة واحدة فقط\n"
            "⏰ تأكد من أن الكود لم تنتهِ صلاحيته"
        )
    else:
        await update.message.reply_text(
            "🎁 **أدخل كود الهدية**\n\n"
            "💡 الكود يستخدم مرة واحدة فقط\n"
            "⏰ تأكد من أن الكود لم تنتهِ صلاحيته"
        )

    return ENTER_CODE


async def process_gift_code(update, context):
    """معالجة كود الهدية المدخل"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    code = update.message.text.strip().upper()
    
    logger.info(f"[GiftCode] User {user_id} entered code: {code}")
    
    try:
        # البحث عن الكود
        result = supa.get_client().table("gift_codes") \
            .select("*") \
            .eq("code", code) \
            .eq("is_used", False) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            logger.warning(f"[GiftCode] Invalid or used code: {code}")
            
            # التحقق إذا كان الكود مستخدم
            used_check = supa.get_client().table("gift_codes") \
                .select("is_used") \
                .eq("code", code) \
                .execute()
            
            if used_check.data and len(used_check.data) > 0:
                await update.message.reply_text(
                    "⚠️ هذا الكود مستخدم مسبقاً.\n\n"
                    "🎁 جرب كود آخر!"
                )
            else:
                await update.message.reply_text(
                    "❌ الكود غير صحيح.\n\n"
                    "🎁 تأكد من إدخال الكود بشكل صحيح"
                )
            
            return ConversationHandler.END
        
        gift = result.data[0]
        amount = gift["amount"]
        
        # ⏰ التحقق من انتهاء صلاحية الكود
        expires_at = gift.get("expires_at")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expiry:
                    await update.message.reply_text(
                        "⏰ **انتهت صلاحية هذا الكود**\n\n"
                        "لم يتم استخدام الكود لأن مدته الزمنية انتهت.\n"
                        "يرجى الحصول على كود جديد."
                    )
                    return ConversationHandler.END
            except:
                pass  # ignore parse errors
        
        # تحديث الكود كمستخدم (نستخدم code كمفتاح أساسي وليس id)
        supa.get_client().table("gift_codes") \
            .update({
                "is_used": True,
                "used_by": user_id,
                "used_at": datetime.now(timezone.utc).isoformat()
            }) \
            .eq("code", gift["code"]) \
            .execute()
        
        # إضافة الرصيد للمستخدم
        current_balance = supa.get_user_balance(user_id)
        new_balance = current_balance + amount
        
        supa.update_user_balance(user_id, new_balance)
        
        # تسجيل العملية
        try:
            supa.log_event(
                event_type="gift_code_used",
                telegram_id=user_id,
                username=username or "",
                details={
                    "code": code,
                    "amount": amount,
                    "gift_code": gift["code"]
                }
            )
        except Exception as log_err:
            logger.warning(f"[GiftCode] Failed to log event: {log_err}")
        
        logger.info(f"[GiftCode] Success: User {user_id} redeemed {amount}")
        
        await update.message.reply_text(
            f"🎉 تهانينا! تم استخدام كود الهدية بنجاح!\n\n"
            f"💰 تم إضافة {amount:,} ل.س لرصيدك\n"
            f"📊 رصيدك الحالي: {new_balance:,} ل.س\n\n"
            f"🎁 استمتع بالهدية!"
        )
        
    except Exception as e:
        logger.error(f"[GiftCode] Error processing code: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ أثناء معالجة الكود.\n"
            "يرجى المحاولة لاحقاً."
        )
    
    return ConversationHandler.END


async def cancel_gift_code(update, context):
    """إلغاء المحادثة"""
    await update.message.reply_text("❌ تم إلغاء العملية.")
    return ConversationHandler.END


async def handle_gift_code_callback(update, context):
    """معالج Callback للزر"""
    await update.callback_query.answer()
    return await handle_gift_code(update, context)

def conversationHandler():
    """إنشاء ConversationHandler"""
    return ConversationHandler(
        entry_points=[
            CommandHandler("gift", handle_gift_code),
            MessageHandler(filters.Regex("^🎁 كود هدية$"), handle_gift_code),
            CallbackQueryHandler(handle_gift_code_callback, pattern='^gift_code$')  # 🔥 من الزر
        ],
        states={
            ENTER_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_gift_code)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_gift_code)
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        per_message=False,
    )
