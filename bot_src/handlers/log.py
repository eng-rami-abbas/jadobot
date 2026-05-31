# log.py (FIXED)

from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import store


class LogHandler:

    @staticmethod
    async def show_log_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        message = """
📜 **سجلك الشخصي**

اختر نوع السجل الذي تريد عرضه:
        """

        keyboard = [
            [InlineKeyboardButton("💰 سجل الشحن", callback_data='log_deposit')],
            [InlineKeyboardButton("💸 سجل السحب", callback_data='log_withdraw')],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_menu')]
        ]

        try:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    @staticmethod
    async def show_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        user_id = query.from_user.id

        transactions = store.get_user_transactions(user_id, 'deposit')

        if not transactions:
            message = "📭 **ليس لديك سجلات شحن بعد**"
        else:
            message = "💰 **سجل الشحن:**\n\n"
            for i, trans in enumerate(transactions[:10], 1):
                # استخدام amount_syp إذا موجود، وإلا amount
                amount = trans.get('amount_syp') or trans.get('amount', 0)
                # تحويل من فئات صغيرة إلى ل.س (قسمة على 100)
                if amount and amount > 1000:
                    amount = amount / 100
                message += f"{i}. #{trans.get('operation_number', trans.get('id', 'N/A'))}\n"
                message += f"   💰 {amount:,.0f} ل.س\n"
                created = trans.get('created_at', 'غير معروف')
                if created and len(created) > 10:
                    created = created[:10]  # اقتطاع التاريخ فقط
                message += f"   📅 {created}\n"
                wallet = trans.get('wallet_name') or trans.get('method') or 'غير محدد'
                message += f"   🏦 {wallet}\n"
                status = trans.get('status', 'pending')
                status_emoji = '⏳' if status == 'pending' else '✅' if status == 'completed' else '❌'
                message += f"   {status_emoji} {status}\n"
                message += "\n"

        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='log')]]

        try:
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    @staticmethod
    async def show_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        user_id = query.from_user.id

        transactions = store.get_user_transactions(user_id, 'withdrawal')

        if not transactions:
            message = "📭 **ليس لديك سجلات سحب بعد**"
        else:
            message = "💸 **سجل السحب:**\n\n"
            for i, trans in enumerate(transactions[:10], 1):
                # استخدام amount_syp إذا موجود، وإلا amount
                amount = trans.get('amount_syp') or trans.get('amount', 0)
                # تحويل من فئات صغيرة إلى ل.س (قسمة على 100)
                if amount and amount > 1000:
                    amount = amount / 100
                message += f"{i}. #{trans.get('operation_number', trans.get('id', 'N/A'))}\n"
                message += f"   💰 {amount:,.0f} ل.س\n"
                created = trans.get('created_at', 'غير معروف')
                if created and len(created) > 10:
                    created = created[:10]  # اقتطاع التاريخ فقط
                message += f"   📅 {created}\n"
                method = trans.get('wallet_name') or trans.get('method') or trans.get('account_number', 'غير محدد')
                message += f"   🏦 {method}\n"
                status = trans.get('status', 'pending')
                status_emoji = '⏳' if status == 'pending' else '✅' if status == 'completed' else '❌'
                message += f"   {status_emoji} {status}\n"
                message += "\n"

        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='log')]]

        try:
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    @staticmethod
    async def handle_log_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        data = query.data

        if data == 'log':
            await LogHandler.show_log_menu(update, context)

        elif data == 'log_deposit':
            await LogHandler.show_deposits(update, context)

        elif data == 'log_withdraw':
            await LogHandler.show_withdrawals(update, context)
