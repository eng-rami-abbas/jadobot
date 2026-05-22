"""
Advanced iChancy Operations Handler
يعالج: شحن، سحب، معلومات الحساب، عمليات، وغيرها
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.iChancyAPI import iChancyAPI
import store
import supabase_integration as supa
import Logger

logger = Logger.getLogger()

# =============================
# 📊 معلومات الحساب (Account Info)
# =============================

async def ichancy_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات الحساب بشكل قابل للنسخ"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        # جلب بيانات الحساب من Supabase
        result = supa.get_client().table("users_ichancy_details") \
            .select("*") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        username = account.get("username", "N/A")
        password = account.get("password", "N/A")
        email = account.get("email", "N/A")
        player_id = account.get("player_id", "N/A")
        
        # جلب الرصيد من API
        api = iChancyAPI()
        balance_result = api.get_player_balance_by_username(username)
        balance = balance_result.get('balance', 0) if balance_result.get('success') else "غير متاح"
        
        # رسالة قابلة للنسخ
        message = (
            f"📋 <b>معلومات الحساب</b>\n\n"
            f"👤 <b>اسم المستخدم:</b>\n<code>{username}</code>\n\n"
            f"🔐 <b>كلمة المرور:</b>\n<code>{password}</code>\n\n"
            f"📧 <b>البريد الإلكتروني:</b>\n<code>{email}</code>\n\n"
            f"🆔 <b>معرف اللاعب:</b>\n<code>{player_id}</code>\n\n"
            f"💰 <b>الرصيد الحالي:</b>\n<code>{balance}</code>"
        )
        
        keyboard = [[
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_ichancy")
        ]]
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_account_info: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


# =============================
# 💰 شحن مع تحديث الرصيد
# =============================

async def ichancy_deposit_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عملية شحن متقدمة مع تحديث الرصيد"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        context.user_data['ichancy_deposit'] = True
        
        await query.edit_message_text(
            "💰 أدخل مبلغ الشحن (بالعملة المحلية):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ إلغاء", callback_data="back_to_ichancy")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_deposit_advanced: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


async def handle_ichancy_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مبلغ الشحن"""
    user_id = str(update.effective_user.id)
    
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من 0")
            return
        
        # جلب بيانات الحساب
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await update.message.reply_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        player_id = account.get("player_id")
        
        # تنفيذ عملية الشحن
        api = iChancyAPI()
        deposit_result = api.deposit_to_player(player_id, amount, f"Telegram Bot Deposit")
        
        if deposit_result.get('success'):
            new_balance = deposit_result.get('new_balance', 0)
            
            message = (
                f"✅ <b>تم الشحن بنجاح!</b>\n\n"
                f"💰 <b>المبلغ:</b> <code>{amount}</code>\n"
                f"💳 <b>الرصيد الجديد:</b> <code>{new_balance}</code>"
            )
            
            # حفظ العملية
            try:
                supa.get_client().table("transactions_ichancy").insert({
                    "telegram_id": user_id,
                    "type": "deposit",
                    "amount": amount,
                    "new_balance": new_balance,
                    "status": "completed"
                }).execute()
            except:
                pass
            
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            error_msg = deposit_result.get('error', 'Unknown error')
            await update.message.reply_text(f"❌ فشل الشحن: {error_msg}")
        
        context.user_data.pop('ichancy_deposit', None)
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
    except Exception as e:
        logger.error(f"Error in handle_ichancy_deposit_amount: {e}")
        await update.message.reply_text(f"❌ خطأ: {str(e)}")


# =============================
# 💸 سحب مع تحديث الرصيد
# =============================

async def ichancy_withdraw_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عملية سحب متقدمة مع تحديث الرصيد"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        context.user_data['ichancy_withdraw'] = True
        
        await query.edit_message_text(
            "💸 أدخل مبلغ السحب (بالعملة المحلية):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ إلغاء", callback_data="back_to_ichancy")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_withdraw_advanced: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


async def handle_ichancy_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مبلغ السحب"""
    user_id = str(update.effective_user.id)
    
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من 0")
            return
        
        # جلب بيانات الحساب
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await update.message.reply_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        player_id = account.get("player_id")
        
        # تنفيذ عملية السحب
        api = iChancyAPI()
        withdraw_result = api.withdraw_from_player(player_id, amount, f"Telegram Bot Withdraw")
        
        if withdraw_result.get('success'):
            new_balance = withdraw_result.get('new_balance', 0)
            
            message = (
                f"✅ <b>تم السحب بنجاح!</b>\n\n"
                f"💸 <b>المبلغ:</b> <code>{amount}</code>\n"
                f"💳 <b>الرصيد الجديد:</b> <code>{new_balance}</code>"
            )
            
            # حفظ العملية
            try:
                supa.get_client().table("transactions_ichancy").insert({
                    "telegram_id": user_id,
                    "type": "withdraw",
                    "amount": amount,
                    "new_balance": new_balance,
                    "status": "completed"
                }).execute()
            except:
                pass
            
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            error_msg = withdraw_result.get('error', 'Unknown error')
            await update.message.reply_text(f"❌ فشل السحب: {error_msg}")
        
        context.user_data.pop('ichancy_withdraw', None)
        
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح")
    except Exception as e:
        logger.error(f"Error in handle_ichancy_withdraw_amount: {e}")
        await update.message.reply_text(f"❌ خطأ: {str(e)}")


async def handle_ichancy_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text input for advanced iChancy deposit/withdraw workflows."""
    if context.user_data.get('ichancy_deposit'):
        await handle_ichancy_deposit_amount(update, context)
        return

    if context.user_data.get('ichancy_withdraw'):
        await handle_ichancy_withdraw_amount(update, context)
        return


# =============================
# 📈 عمليات (Transactions)
# =============================

async def ichancy_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر العمليات"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        # جلب آخر 10 عمليات
        result = supa.get_client().table("transactions_ichancy") \
            .select("*") \
            .eq("telegram_id", user_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        
        transactions = result.data if result.data else []
        
        if not transactions:
            message = "📊 <b>لا توجد عمليات</b>"
        else:
            message = "📊 <b>آخر العمليات:</b>\n\n"
            for tx in transactions:
                tx_type = "💰 شحن" if tx.get("type") == "deposit" else "💸 سحب"
                amount = tx.get("amount", 0)
                balance = tx.get("new_balance", 0)
                
                message += (
                    f"{tx_type}\n"
                    f"المبلغ: <code>{amount}</code>\n"
                    f"الرصيد: <code>{balance}</code>\n"
                    f"─────────────────\n"
                )
        
        keyboard = [[
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_ichancy")
        ]]
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in ichancy_transactions: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")


# =============================
# ⚡ شحن كامل الرصيد (محسّن)
# =============================

async def ichancy_deposit_all_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شحن كامل الرصيد مع تحديث كامل"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    
    try:
        # جلب بيانات الحساب
        result = supa.get_client().table("users_ichancy_details") \
            .select("username, player_id") \
            .eq("telegram_id", user_id) \
            .execute()
        
        if not result.data:
            await query.edit_message_text("❌ لم يتم العثور على حساب")
            return
        
        account = result.data[0]
        player_id = account.get("player_id")
        
        # جلب الرصيد الحالي
        api = iChancyAPI()
        balance_result = api.get_player_balance_by_id(player_id)
        
        if not balance_result.get('success'):
            await query.edit_message_text("❌ لا يمكن جلب الرصيد")
            return
        
        current_balance = balance_result.get('balance', 0)
        
        if current_balance <= 0:
            await query.edit_message_text("❌ لا يوجد رصيد للشحن")
            return
        
        # سحب كامل الرصيد
        withdraw_result = api.withdraw_from_player(
            player_id, 
            current_balance, 
            "Telegram Bot - Transfer All"
        )
        
        if withdraw_result.get('success'):
            message = (
                f"✅ <b>تم شحن كامل الرصيد!</b>\n\n"
                f"💰 <b>المبلغ المشحون:</b> <code>{current_balance}</code>"
            )
            
            # حفظ العملية
            try:
                supa.get_client().table("transactions_ichancy").insert({
                    "telegram_id": user_id,
                    "type": "transfer_all",
                    "amount": current_balance,
                    "new_balance": 0,
                    "status": "completed"
                }).execute()
            except:
                pass
            
            await query.edit_message_text(message, parse_mode="HTML")
        else:
            await query.edit_message_text(f"❌ فشل العملية: {withdraw_result.get('error', 'Unknown')}")
            
    except Exception as e:
        logger.error(f"Error in ichancy_deposit_all_advanced: {e}")
        await query.edit_message_text(f"❌ خطأ: {str(e)}")
