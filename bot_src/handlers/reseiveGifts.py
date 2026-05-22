from datetime import datetime, timezone
from bot import supabase
from config.telegram import CallbackQuery ,Update ,ReplyKeyboardRemove
from telegram.ext import ConversationHandler , CallbackQueryHandler ,MessageHandler ,filters ,CallbackContext ,CommandHandler
import store
CODE = range(1)
from bot import exchange_rate_cache

rate = exchange_rate_cache

async def button_reseive_gift_handler(update: Update , context:CallbackContext ):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎁 **أدخل كود الهدية**\n\n"
        "💡 الكود يستخدم مرة واحدة فقط\n"
        "⏰ تأكد من أن الكود لم تنتهِ صلاحيته"
    )
    return CODE

async def get_code(update: Update, context: CallbackContext):
    code = update.message.text
    telegram_id = update.message.from_user.id

    # 1. جلب الكود
    res = supabase.table("gift_codes").select("*").eq("code", code).execute()

    if not res.data:
        await update.message.reply_text("❌ الكود غير صحيح")
        return ConversationHandler.END

    gift = res.data[0]

    # 2. تحقق إذا مستخدم (is_used وليس used)
    if gift.get("is_used", False):
        await update.message.reply_text("❌ هذا الكود مستخدم مسبقاً")
        return ConversationHandler.END

    # 3. تحقق انتهاء الصلاحية
    expires_at = gift.get("expires_at")
    if expires_at:
        try:
            expire_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expire_time:
                await update.message.reply_text(
                    "⏰ **انتهت صلاحية هذا الكود**\n\n"
                    "لم يتم استخدام الكود لأن مدته الزمنية انتهت.\n"
                    "يرجى الحصول على كود جديد."
                )
                return ConversationHandler.END
        except Exception as e:
            print(f"[Gift] Error parsing expiry: {e}")
            pass  # ignore date parsing errors

    amount = gift["amount"]

    # 4. إضافة الرصيد (RPC)
    supabase.rpc("increment_balance", {
        "uid": telegram_id,
        "amount": amount,
        "currency": "syp",
        "exchange_rate": 1
    }).execute()
    
    supabase.rpc("increment_balance", {
        "uid": telegram_id,
        "amount": amount,
        "currency": "usd",
        "exchange_rate": 15000  # أو من إعداداتك
    }).execute()
    
    # 5. تحديث الكود كمستخدم
    supabase.table("gift_codes").update({
        "is_used": True,
        "used_by": telegram_id,
        "used_at": datetime.now(timezone.utc).isoformat()
    }).eq("code", code).execute()

    await update.message.reply_text(
        f"🎉 **تم استخدام كود الهدية بنجاح!**\n\n"
        f"💰 تم إضافة {amount:,} ل.س لرصيدك\n"
        f"📊 رصيدك الحالي متاح في القائمة الرئيسية"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        'تم إلغاء عملية إهداء الرصيد',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points= [CallbackQueryHandler(button_reseive_gift_handler , pattern='^reseive_gift$')],
        states={
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND , get_code)]
        },
     fallbacks=[CommandHandler('cancel', cancel)],
    )
    return conv_handler