from telegram.ext import filters, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, CommandHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from services.iChancyAPI import iChancyAPI
import random, string, asyncio
from datetime import datetime
import handlers.ichancy
import supabase_integration as supa
import Logger

logger = Logger.getLogger()

NAME, PASSWORD, EMAIL, AMOUNT = range(4)


def generateRandomString(length=5):
    return ''.join(random.choices(string.ascii_letters, k=length))


async def button_create_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.callback_query.from_user.id
    account = supa.get_ichancy_details_by_telegram_id(telegram_id)

    if account and account.get('username'):
        await update.callback_query.answer("لديك حساب مسجل مسبقا", show_alert=True)
        return ConversationHandler.END

    await update.callback_query.edit_message_text("ادخل اسم حساب الـ Ichancy الجديد")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text

    if len(name) < 4:
        await update.message.reply_text("الاسم يجب أن يكون على الأقل 4 أحرف")
        return NAME

    context.user_data['name'] = name
    await update.message.reply_text("ادخل كلمة سر للحساب الجديد (8 أحرف على الأقل)")
    return PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text

    if len(password) < 8:
        await update.message.reply_text("كلمة السر يجب أن تكون 8 أحرف على الأقل")
        return PASSWORD

    context.user_data['password'] = password

    # توليد email فريد
    random_suffix = generateRandomString(6).lower()
    base_name = context.user_data['name'].lower()
    base_name_clean = ''.join(c if c.isalnum() else '' for c in base_name)
    email = f"{base_name_clean}_{random_suffix}@jadobot.jado"

    context.user_data['email'] = email

    await update.message.reply_text(f"تم توليد بريد إلكتروني: {email}")
    await update.message.reply_text("جاري إنشاء الحساب... ⏳")

    asyncio.create_task(handle_create_account(update, context))

    return ConversationHandler.END


async def handle_create_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إنشاء الحساب"""
    try:
        telegram_user_id = str(update.effective_user.id)
        name = context.user_data.get('name')
        password = context.user_data.get('password')
        email = context.user_data.get('email')

        logger.info(f"Creating account for user {telegram_user_id}: {name}")
        logger.info(f"Email: {email}, using parent_id: {handlers.ichancy.PARENT_ID}")

        api = iChancyAPI()

        # REGISTER ACCOUNT
        result = api.register_player(
            username=name,
            password=password,
            email=email,
            parent_id=handlers.ichancy.PARENT_ID
        )

        logger.info(f"Register result: {result}")

        await asyncio.sleep(3)

        # VERIFY USER
        verify = None
        for i in range(5):
            try:
                verify = api.get_player_id_by_username(name)
                logger.info(f"Verification attempt {i+1}: {verify}")
            except Exception as e:
                logger.error(f"VERIFY ERROR (attempt {i+1}): {e}")
                verify = None

            if verify:
                break
            await asyncio.sleep(1)

        logger.info(f"VERIFY RESULT: {verify}")

        # SUCCESS CHECK
        if result.get('success'):
            player_id = verify
            if not player_id:
                try:
                    player_id = api.get_player_id_by_username(name)
                except Exception as e:
                    logger.error(f"PLAYER ID ERROR: {e}")
                    player_id = result.get('player_id', None)

            # DATABASE
            try:
                supa.upsert_user(
                    telegram_id=int(telegram_user_id),
                    username=update.effective_user.username or "",
                    first_name=update.effective_user.first_name or "",
                    last_name=update.effective_user.last_name or ""
                )
            except Exception as e:
                logger.warning(f"Could not upsert user meta to Supabase: {e}")

            try:
                supa.upsert_ichancy_details(
                    telegram_id=telegram_user_id,
                    username=name,
                    email=email,
                    password=password,
                    player_id=player_id or "0"
                )
                logger.info(f"Saved ichancy details to Supabase for user {telegram_user_id}")
            except Exception as e:
                logger.warning(f"Could not save ichancy details to Supabase: {e}")

            # MESSAGE SUCCESS
            success_message = (
                f"✅ تم إنشاء الحساب بنجاح!\n\n"
                f"👤 الحساب: {name}\n"
                f"🔒 كلمة السر: {password}\n"
                f"📧 الإيميل: {email}\n"
                f"🆔 رقم اللاعب: {player_id if player_id else 'قيد المعالجة'}\n\n"
                f"رابط الدخول: https://www.ichancy.com/ar"
            )

            await update.message.reply_text(success_message, parse_mode=None)

            from handlers.ichancy import get_ichancy_keyboard
            await update.message.reply_text(
                "🎮 القائمة:",
                reply_markup=get_ichancy_keyboard(telegram_user_id)
            )

        else:
            error_msg = result.get('error', 'Unknown error')

            if 'Authentication failed' in error_msg:
                user_error = (
                    "❌ خطأ في الاتصال بخوادم ichancy\n\n"
                    "السبب المحتمل:\n"
                    "• بيانات الدخول غير صحيحة\n"
                    "• تم تعطيل الحساب\n"
                    "• مشكلة في الاتصال\n\n"
                    "الحل:\n"
                    "تواصل مع الإدارة: @jadobotichancy"
                )
            elif 'Duplicate login' in error_msg or 'duplicate' in error_msg.lower():
                user_error = "❌ اسم المستخدم مستخدم بالفعل! الرجاء اختيار اسم آخر."
            elif 'email' in error_msg.lower():
                user_error = f"❌ خطأ في البريد الإلكتروني: {error_msg}\n\nحاول مرة أخرى."
            elif 'password' in error_msg.lower():
                user_error = f"❌ خطأ في كلمة السر: {error_msg}\n\nيجب أن تكون على الأقل 3 أحرف."
            elif 'parent' in error_msg.lower():
                user_error = "❌ خطأ في نظام الإحالة. تواصل مع الدعم."
            else:
                user_error = f"❌ خطأ:\n{error_msg}"

            raise Exception(user_error)

    except Exception as e:
        error_text = str(e)
        logger.error(f"ERROR IN CREATE ACCOUNT: {error_text}", exc_info=True)
        await update.message.reply_text(error_text)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        'تم إلغاء إنشاء الحساب',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_create_account_handler, pattern='^ichancy_create_account$')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True,
        per_user=True,
        allow_reentry=True,
    )
    return conv_handler
