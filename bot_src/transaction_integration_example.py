"""
Example of how to integrate transaction notifications into existing handlers
This file shows the pattern to follow for other deposit/withdrawal handlers
"""

import Logger
import store
from services.transaction_notification_service import transaction_notification_service

logger = Logger.getLogger()

async def example_deposit_handler(update, context):
    """
    Example of how to integrate transaction notifications into a deposit handler
    """
    try:
        user_id = str(update.effective_user.id)
        amount = context.user_data.get('amount')
        provider_type = 'bemo'  # or 'payeer', 'crypto', etc.
        transfer_num = context.user_data.get('transfer_num')
        
        # 1. Create transaction in database
        transaction_id = store.insertTransaction(
            telegram_id=user_id,
            value=amount,
            action_type='deposit',
            provider_type=provider_type,
            transfer_num=transfer_num
        )
        
        if not transaction_id:
            await update.message.reply_text("❌ Error creating transaction. Please try again.")
            return
        
        # 2. Send notification to admin
        await transaction_notification_service.notify_admin_new_transaction(
            transaction_id, provider_type
        )
        
        # 3. Inform user that request is under review
        success_message = f"""
✅ طلب الإيداع تم إرساله بنجاح

💰 المبلغ: {amount} SYP
🏦 الطريقة: {provider_type.title()}
🆔 رقم الطلب: #{transaction_id}

⏳ تم إرسال طلبك للمراجعة. سيتم إشعارك عند الموافقة أو الرفض.
        """
        
        await update.message.reply_text(success_message)
        
    except Exception as e:
        logger.error(f"Error in example deposit handler: {e}")
        await update.message.reply_text("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")

async def example_withdrawal_handler(update, context):
    """
    Example of how to integrate transaction notifications into a withdrawal handler
    """
    try:
        user_id = str(update.effective_user.id)
        amount = context.user_data.get('amount')
        provider_type = 'bemo'  # or 'payeer', 'crypto', etc.
        account_details = context.user_data.get('account_details')
        
        # Check if user has sufficient balance
        current_balance = store.get_user_balance(store.getUserByTelegramId(user_id)['id'])
        if current_balance < amount:
            await update.message.reply_text("❌ رصيدك غير كافي لهذا السحب.")
            return
        
        # 1. Create transaction in database
        transaction_id = store.insertTransaction(
            telegram_id=user_id,
            value=amount,
            action_type='withdrawal',
            provider_type=provider_type,
            transfer_num=account_details  # or account number
        )
        
        if not transaction_id:
            await update.message.reply_text("❌ Error creating transaction. Please try again.")
            return
        
        # 2. Send notification to admin
        await transaction_notification_service.notify_admin_new_transaction(
            transaction_id, provider_type
        )
        
        # 3. Inform user that request is under review
        success_message = f"""
✅ طلب السحب تم إرساله بنجاح

💰 المبلغ: {amount} SYP
🏦 الطريقة: {provider_type.title()}
🆔 رقم الطلب: #{transaction_id}

⏳ تم إرسال طلبك للمراجعة. سيتم إشعارك عند الموافقة أو الرفض.
        """
        
        await update.message.reply_text(success_message)
        
    except Exception as e:
        logger.error(f"Error in example withdrawal handler: {e}")
        await update.message.reply_text("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")

# Integration checklist for existing handlers:
"""
1. Import the notification service:
   from services.transaction_notification_service import transaction_notification_service

2. After creating a transaction, add:
   await transaction_notification_service.notify_admin_new_transaction(transaction_id, provider_type)

3. Update success message to inform user about review process:
   "⏳ تم إرسال طلبك للمراجعة. سيتم إشعارك عند الموافقة أو الرفض."

4. For withdrawals, add balance check before creating transaction:
   current_balance = store.get_user_balance(user_id)
   if current_balance < amount:
       # Handle insufficient balance
"""
