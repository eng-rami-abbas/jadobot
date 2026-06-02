import Logger
import store
import handlers.transactions
from config.telegram import Bot
from config.telegram import TOKEN

logger = Logger.getLogger()

class TransactionNotificationService:
    """Service to handle transaction notifications to admin"""
    
    def __init__(self):
        self.bot = Bot(token=TOKEN)
    
    async def notify_admin_new_transaction(self, transaction_id, transaction_type='general'):
        """Send notification to admin about new transaction"""
        try:
            # Get transaction details
            transaction = store.get_transaction_by_id(transaction_id, transaction_type)
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found for notification")
                return False
            
            # Send notification to admin
            await handlers.transactions.send_transaction_to_admin(transaction, transaction_type)
            logger.info(f"Transaction {transaction_id} notification sent to admin")
            return True
            
        except Exception as e:
            logger.error(f"Error sending transaction notification: {e}")
            return False
    
    async def notify_user_transaction_update(self, transaction_id, status):
        """Notify user about transaction status update"""
        try:
            transaction = store.get_transaction_by_id(transaction_id)
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found for user notification")
                return False
            
            await handlers.transactions.notify_user_transaction_status(transaction, status)
            logger.info(f"Transaction {transaction_id} status update sent to user")
            return True
            
        except Exception as e:
            logger.error(f"Error sending user notification: {e}")
            return False

# Global instance
transaction_notification_service = TransactionNotificationService()
