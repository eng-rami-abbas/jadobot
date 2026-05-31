"""
نظام الإشعارات المتقدم
"""

import logging
import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any

import Logger
import config.telegram
import store
from config.telegram import Bot, Update
from telegram.ext import ContextTypes

logger = Logger.getLogger()

class NotificationSystem:
    """نظام الإشعارات المتقدم"""
    
    def __init__(self):
        self.bot = Bot(token=config.telegram.TOKEN)
        self.notification_queue = []
        self.is_running = False
        
        logger.info("Notification system initialized")
    
    async def send_instant_notification(self, user_id: str, message: str, notification_type: str = "info"):
        """إرسال إشعار فوري"""
        try:
            emoji = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
                "promo": "🎁",
                "update": "🔄"
            }.get(notification_type, "📨")
            
            formatted_message = f"{emoji} {message}"
            
            await self.bot.send_message(
                chat_id=user_id,
                text=formatted_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Notification sent to {user_id}: {notification_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification to {user_id}: {e}")
            return False
    
    async def send_bulk_notification(self, user_ids: List[str], message: str, notification_type: str = "info"):
        """إرسال إشعار جماعي"""
        results = {
            "success": 0,
            "failed": 0,
            "failed_ids": []
        }
        
        for user_id in user_ids:
            success = await self.send_instant_notification(user_id, message, notification_type)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_ids"].append(user_id)
            
            # تأخير صغير لتجنب حظر التليجرام
            await asyncio.sleep(0.1)
        
        logger.info(f"Bulk notification results: {results['success']}成功, {results['failed']} فشل")
        return results
    
    async def send_transaction_notification(self, user_id: str, transaction_type: str, amount: int, status: str, transaction_id: str = None):
        """إرسال إشعار معاملة"""
        status_emoji = {
            "pending": "⏳",
            "completed": "✅",
            "failed": "❌",
            "rejected": "🚫"
        }.get(status, "❓")
        
        type_text = {
            "deposit": "إيداع",
            "withdrawal": "سحب",
            "transfer": "تحويل",
            "gift": "هدية",
            "referral": "إحالة"
        }.get(transaction_type, transaction_type)
        
        message = f"""
{status_emoji} **إشعار معاملة**

💰 **النوع:** {type_text}
💵 **المبلغ:** {helpers.format_currency(amount)}
📊 **الحالة:** {status}

{f'🆔 **رقم المعاملة:** #{transaction_id}' if transaction_id else ''}
📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        return await self.send_instant_notification(user_id, message, "info")
    
    async def send_promo_notification(self, user_id: str, title: str, description: str, expiry_date: str = None):
        """إرسال إشعار ترويجي"""
        message = f"""
🎁 **عرض خاص!**

**{title}**

{description}

{f'⏰ **ينتهي في:** {expiry_date}' if expiry_date else ''}

🚀 **استفد من العرض الآن!**
        """
        
        return await self.send_instant_notification(user_id, message, "promo")
    
    async def send_system_update(self, user_id: str, update_type: str, description: str, version: str = None):
        """إرسال إشعار تحديث نظام"""
        message = f"""
🔄 **تحديث النظام**

**{update_type}**

{description}

{f'📱 **الإصدار:** {version}' if version else ''}

🔧 **شكراً لاستخدامك iChancy Bot**
        """
        
        return await self.send_instant_notification(user_id, message, "update")
    
    def schedule_daily_notification(self, user_id: str, message: str, time_str: str):
        """جدولة إشعار يومي"""
        try:
            schedule.every().day.at(time_str).do(
                lambda: asyncio.create_task(self.send_instant_notification(user_id, message))
            )
            logger.info(f"Daily notification scheduled for {user_id} at {time_str}")
            return True
        except Exception as e:
            logger.error(f"Error scheduling daily notification: {e}")
            return False
    
    def schedule_weekly_report(self, user_id: str, day: str = "sunday", time_str: str = "10:00"):
        """جدولة تقرير أسبوعي"""
        try:
            getattr(schedule.every(), day).at(time_str).do(
                lambda: asyncio.create_task(self.send_weekly_report(user_id))
            )
            logger.info(f"Weekly report scheduled for {user_id} on {day} at {time_str}")
            return True
        except Exception as e:
            logger.error(f"Error scheduling weekly report: {e}")
            return False
    
    async def send_weekly_report(self, user_id: str):
        """إرسال تقرير أسبوعي"""
        try:
            # جلب بيانات الأسبوع
            message = """
📊 **تقريرك الأسبوعي**

💰 **الإيداعات هذا الأسبوع:** 0 ليرة
💸 **السحوبات هذا الأسبوع:** 0 ليرة
👥 **الإحالات الجديدة:** 0
🎁 **الهدايا المرسلة:** 0

📈 **ملخص الأداء:**
• نشاطك: ممتاز
• أرباح الإحالة: 0 ليرة
• الرصيد الحالي: 0 ليرة

🎯 **نصيحة الأسبوع:**
شارك رابط الإحالة لزيادة أرباحك!
            """
            
            await self.send_instant_notification(user_id, message, "info")
            return True
        except Exception as e:
            logger.error(f"Error sending weekly report: {e}")
            return False
    
    def start_scheduler(self):
        """بدء المجدول"""
        try:
            def run_scheduler():
                while self.is_running:
                    schedule.run_pending()
                    time.sleep(60)
            
            self.is_running = True
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            
            logger.info("Notification scheduler started")
            return True
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return False
    
    def stop_scheduler(self):
        """إيقاف المجدول"""
        self.is_running = False
        logger.info("Notification scheduler stopped")
    
    def add_to_queue(self, notification: Dict[str, Any]):
        """إضافة إشعار إلى قائمة الانتظار"""
        self.notification_queue.append(notification)
        logger.info(f"Notification added to queue: {notification.get('type')}")
    
    async def process_queue(self):
        """معالجة قائمة الانتظار"""
        while self.notification_queue:
            notification = self.notification_queue.pop(0)
            try:
                await self.send_instant_notification(
                    notification['user_id'],
                    notification['message'],
                    notification.get('type', 'info')
                )
            except Exception as e:
                logger.error(f"Error processing queued notification: {e}")

# إنشاء نسخة عالمية
notification_system = NotificationSystem()

def initialize_notification_system():
    """تهيئة نظام الإشعارات"""
    notification_system.start_scheduler()
    logger.info("Notification system initialized")