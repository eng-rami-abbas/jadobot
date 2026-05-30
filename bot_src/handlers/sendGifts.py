import Logger
import supabase_integration as supa
from utils import helpers
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler,
)
from datetime import datetime, timezone

logger = Logger.getLogger()

# 🔥 نسبة العمولة 10%
COMMISSION_RATE = 0.10
# 🔥 حساب البوت الرئيسي
BOT_ADMIN_ID = 7179419936

# States
telegramIdGoal, amount, confirm = range(3)

async def button_send_gifts_handler(update: Update, context: CallbackContext) -> int:
    """معالجة الضغط على زر إهداء رصيد"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = str(update.effective_user.id)
    
    # 🔥 التحقق من الرصيد قبل بدء المحادثة
    balance = supa.get_user_balance(int(telegram_id))
    if balance <= 0:
        await query.edit_message_text(
            "❌ **ليس لديك رصيد كافٍ للإهداء**\n\n"
            "💰 رصيدك الحالي: 0 ل.س\n\n"
            "📥 قم بشحن رصيدك أولاً من خلال زر 'شحن رصيد'"
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"🎁 **إهداء رصيد مباشر**\n\n"
        f"💰 رصيدك الحالي: {balance:,.0f} ل.س\n"
        f"📊 العمولة: {int(COMMISSION_RATE * 100)}%\n\n"
        f"👤 أرسل معرف Telegram للشخص المراد إهداؤه:\n"
        f"💡 يمكن الحصول عليه من زر 'رصيدي'\n\n"
        f"📱 معرفك: `{telegram_id}`",
        parse_mode='Markdown'
    )
    return telegramIdGoal


async def get_telegram_id_goal(update: Update, context: CallbackContext) -> int:
    """حفظ معرف المستلم والتحقق منه"""
    user = update.message.from_user
    telegram_id = str(update.effective_user.id)
    recipient_id = update.message.text.strip()
    
    # التحقق من صحة المعرف
    try:
        recipient_id_int = int(recipient_id)
        if recipient_id_int <= 0:
            raise ValueError("Invalid ID")
    except ValueError:
        await update.message.reply_text(
            "❌ **معرف Telegram غير صحيح**\n\n"
            "يرجى إدخال رقم صحيح (مثال: 123456789)"
        )
        return telegramIdGoal
    
    # منع الإهداء لنفسك
    if str(recipient_id_int) == telegram_id:
        await update.message.reply_text(
            "❌ **لا يمكنك إهداء الرصيد لنفسك!**\n\n"
            "أدخل معرف شخص آخر."
        )
        return telegramIdGoal
    
    # التحقق من وجود المستلم في قاعدة البيانات
    try:
        recipient_balance = supa.get_user_balance(recipient_id_int)
        # إذا وصلنا هنا، المستخدم موجود (حتى لو الرصيد 0)
    except Exception:
        await update.message.reply_text(
            "❌ **المستخدم غير موجود**\n\n"
            "تأكد من المعرف أو اطلب منه التسجيل في البوت أولاً."
        )
        return telegramIdGoal
    
    context.user_data['recipient_id'] = recipient_id
    context.user_data['recipient_id_int'] = recipient_id_int
    logger.info("User %s wants to gift to: %s", user.first_name, recipient_id)
    
    # عرض الرصيد وطلب المبلغ
    balance = supa.get_user_balance(int(telegram_id))
    
    await update.message.reply_text(
        f"✅ **تم العثور على المستلم**\n\n"
        f"👤 معرف المستلم: `{recipient_id}`\n"
        f"💰 رصيدك: {balance:,.0f} ل.س\n"
        f"📊 العمولة: {int(COMMISSION_RATE * 100)}%\n\n"
        f"💸 أدخل المبلغ المراد إهداؤه (بالليرة السورية):"
    )
    return amount


async def get_amount(update: Update, context: CallbackContext) -> int:
    """حفظ المبلغ وعرض تأكيد"""
    user = update.message.from_user
    telegram_id = str(update.effective_user.id)
    recipient_id = context.user_data.get('recipient_id')
    recipient_id_int = context.user_data.get('recipient_id_int')
    
    # التحقق من صحة المبلغ
    try:
        gift_amount = float(update.message.text.strip())
        if gift_amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await update.message.reply_text(
            "❌ **المبلغ غير صحيح**\n\n"
            "يرجى إدخال رقم صحيح أكبر من صفر."
        )
        return amount
    
    # حساب العمولة والإجمالي
    commission = gift_amount * COMMISSION_RATE
    total_deduction = gift_amount + commission
    
    # التحقق من الرصيد
    sender_balance = supa.get_user_balance(int(telegram_id))
    
    if sender_balance < total_deduction:
        await update.message.reply_text(
            f"❌ **رصيدك غير كافٍ**\n\n"
            f"💰 رصيدك: {sender_balance:,.0f} ل.س\n"
            f"💸 المطلوب: {total_deduction:,.0f} ل.س\n"
            f"  - المبلغ: {gift_amount:,.0f} ل.س\n"
            f"  - العمولة ({int(COMMISSION_RATE * 100)}%): {commission:,.0f} ل.س\n\n"
            f"📥 يرجى شحن رصيدك أولاً."
        )
        return ConversationHandler.END
    
    # حفظ البيانات للتأكيد
    context.user_data['gift_amount'] = gift_amount
    context.user_data['commission'] = commission
    context.user_data['total_deduction'] = total_deduction
    
    # عرض رسالة التأكيد
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد الإهداء", callback_data="confirm_gift")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_gift")]
    ])
    
    await update.message.reply_text(
        f"🎁 **تأكيد عملية الإهداء**\n\n"
        f"👤 **من:** `{telegram_id}`\n"
        f"🎯 **إلى:** `{recipient_id}`\n\n"
        f"💰 **المبلغ:** {gift_amount:,.0f} ل.س\n"
        f"📊 **العمولة ({int(COMMISSION_RATE * 100)}%):** {commission:,.0f} ل.س\n"
        f"💸 **الإجمالي للخصم:** {total_deduction:,.0f} ل.س\n\n"
        f"💳 **رصيدك بعد العملية:** {sender_balance - total_deduction:,.0f} ل.س\n\n"
        f"⚡ **سيتم التحويل فوراً بعد التأكيد**",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return confirm


async def confirm_gift(update: Update, context: CallbackContext) -> int:
    """تنفيذ التحويل بعد التأكيد"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_id = str(user.id)
    
    # استرجاع البيانات
    recipient_id = context.user_data.get('recipient_id')
    recipient_id_int = context.user_data.get('recipient_id_int')
    gift_amount = context.user_data.get('gift_amount')
    commission = context.user_data.get('commission')
    total_deduction = context.user_data.get('total_deduction')
    
    if not all([recipient_id, recipient_id_int, gift_amount]):
        await query.edit_message_text("❌ حدث خطأ: بيانات غير مكتملة")
        return ConversationHandler.END
    
    try:
        # 🔥 تنفيذ التحويل
        sender_balance = supa.get_user_balance(int(telegram_id))
        recipient_balance = supa.get_user_balance(recipient_id_int)
        bot_admin_balance = supa.get_user_balance(BOT_ADMIN_ID)
        
        # التحقق مرة أخرى من الرصيد
        if sender_balance < total_deduction:
            await query.edit_message_text(
                "❌ **رصيدك غير كافٍ**\n\n"
                "يبدو أن رصيدك تغير. يرجى المحاولة مرة أخرى."
            )
            return ConversationHandler.END
        
        # 1. خصم الإجمالي من المرسل
        new_sender_balance = sender_balance - total_deduction
        supa.update_user_balance(int(telegram_id), new_sender_balance)
        
        # 2. إضافة المبلغ للمستلم
        new_recipient_balance = recipient_balance + gift_amount
        supa.update_user_balance(recipient_id_int, new_recipient_balance)
        
        # 3. إضافة العمولة لحساب البوت
        new_bot_balance = bot_admin_balance + commission
        supa.update_user_balance(BOT_ADMIN_ID, new_bot_balance)
        
        # تسجيل العملية
        try:
            supa.log_event(
                event_type="gift_transfer_direct",
                telegram_id=int(telegram_id),
                username=user.username or "",
                details={
                    "recipient_id": recipient_id_int,
                    "amount": gift_amount,
                    "commission": commission,
                    "total_deduction": total_deduction,
                    "sender_new_balance": new_sender_balance,
                    "recipient_new_balance": new_recipient_balance
                }
            )
        except Exception as log_err:
            logger.warning(f"[SendGift] Failed to log event: {log_err}")
        
        # ✅ رسالة نجاح للمرسل
        await query.edit_message_text(
            f"🎉 **تم الإهداء بنجاح!**\n\n"
            f"👤 **المستلم:** `{recipient_id}`\n"
            f"💰 **المبلغ:** {gift_amount:,.0f} ل.س\n"
            f"📊 **العمولة:** {commission:,.0f} ل.س\n"
            f"💸 **تم الخصم:** {total_deduction:,.0f} ل.س\n"
            f"💳 **رصيدك المتبقي:** {new_sender_balance:,.0f} ل.س\n\n"
            f"✅ تم إرسال إشعار للمستلم",
            parse_mode='Markdown'
        )
        
        # 🔥 إرسال إشعار للمستلم
        try:
            from telegram import Bot
            from config.telegram import TOKEN
            bot = Bot(token=TOKEN)
            
            await bot.send_message(
                chat_id=recipient_id_int,
                text=(
                    f"🎁 **لقد تلقيت هدية!**\n\n"
                    f"👤 **من:** `{telegram_id}`\n"
                    f"💰 **المبلغ:** {gift_amount:,.0f} ل.س\n"
                    f"📊 **رصيدك الحالي:** {new_recipient_balance:,.0f} ل.س\n\n"
                    f"✅ تم إضافة المبلغ لرصيدك تلقائياً"
                ),
                parse_mode='Markdown'
            )
        except Exception as notify_err:
            logger.warning(f"[SendGift] Failed to notify recipient: {notify_err}")
        
        logger.info(f"[SendGift] Success: {telegram_id} sent {gift_amount} to {recipient_id}")
        
    except Exception as e:
        logger.error(f"[SendGift] Error during transfer: {e}")
        await query.edit_message_text(
            "❌ **حدث خطأ أثناء التحويل**\n\n"
            "يرجى المحاولة لاحقاً أو التواصل مع الدعم."
        )
    
    return ConversationHandler.END


async def cancel_gift_callback(update: Update, context: CallbackContext) -> int:
    """إلغاء من الزر"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "❌ تم إلغاء عملية الإهداء",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    """إلغاء المحادثة"""
    await update.message.reply_text(
        '❌ تم إلغاء عملية إهداء الرصيد',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_send_gifts_handler, pattern='^send_gift$')],
        states={
            telegramIdGoal: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_telegram_id_goal)],
            amount: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            confirm: [
                CallbackQueryHandler(confirm_gift, pattern='^confirm_gift$'),
                CallbackQueryHandler(cancel_gift_callback, pattern='^cancel_gift$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True,
        allow_reentry=True,
        per_message=True,
    )
    return conv_handler
