"""
نظام النسخ الاحتياطي التلقائي
"""

import os
import shutil
import logging
import schedule
import time
import threading
import zipfile
from datetime import datetime, timedelta
import sqlite3
import json
from pathlib import Path

import Logger
import config.telegram
from config.telegram import Bot

logger = Logger.getLogger()

class BackupSystem:
    """نظام النسخ الاحتياطي الشامل"""
    
    def __init__(self):
        self.backup_dir = "backups"
        self.logs_dir = "logs"
        self.data_dir = "data"
        self.config_dir = "config"
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # إنشاء مجلدات النسخ الاحتياطي
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, "daily"), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, "weekly"), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, "monthly"), exist_ok=True)
        
        logger.info("Backup system initialized")
    
    def backup_database(self):
        """نسخ قاعدة البيانات"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, "daily", f"database_{timestamp}.db")
            
            # نسخ قاعدة البيانات
            if os.path.exists("data/bot_database.db"):
                shutil.copy2("data/bot_database.db", backup_file)
                logger.info(f"Database backup created: {backup_file}")
                return backup_file
            else:
                logger.warning("Database file not found")
                return None
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return None
    
    def backup_logs(self):
        """نسخ ملفات السجلات"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, "daily", f"logs_{timestamp}.zip")
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if not os.path.exists(self.logs_dir):
                    return None
                for root, dirs, files in os.walk(self.logs_dir):
                    for file in files:
                        if file.endswith('.log'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, self.logs_dir)
                            zipf.write(file_path, arcname)
            
            logger.info(f"Logs backup created: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Error backing up logs: {e}")
            return None
    
    def backup_configs(self):
        """نسخ ملفات الإعدادات"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, "daily", f"configs_{timestamp}.zip")
            
            config_files = [
                "config/telegram.py",
                "config/ichancy.py",
                "config/database.py",
                "config/device.py",
                ".env"
            ]
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for config_file in config_files:
                    if os.path.exists(config_file):
                        zipf.write(config_file, os.path.basename(config_file))
            
            logger.info(f"Configs backup created: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Error backing up configs: {e}")
            return None
    
    def create_full_backup(self):
        """إنشاء نسخة احتياطية كاملة"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"full_backup_{timestamp}.zip")
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # إضافة قاعدة البيانات
                if os.path.exists("data/bot_database.db"):
                    zipf.write("data/bot_database.db", "database.db")
                
                # إضافة السجلات
                for root, dirs, files in os.walk(self.logs_dir):
                    for file in files:
                        if file.endswith('.log'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("logs", os.path.relpath(file_path, self.logs_dir))
                            zipf.write(file_path, arcname)
                
                # إضافة الإعدادات
                config_files = [
                    "config/telegram.py",
                    "config/ichancy.py",
                    "config/database.py",
                    "config/device.py",
                    ".env",
                    "requirements.txt",
                    "bot.py"
                ]
                
                for config_file in config_files:
                    if os.path.exists(config_file):
                        zipf.write(config_file, os.path.basename(config_file))
            
            logger.info(f"Full backup created: {backup_file}")
            
            # إرسال إشعار للإدمن
            self.notify_admin_backup(backup_file)
            
            return backup_file
        except Exception as e:
            logger.error(f"Error creating full backup: {e}")
            return None
    
    def cleanup_old_backups(self, days=30):
        """تنظيف النسخ القديمة"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for backup_type in ["daily", "weekly", "monthly"]:
                backup_path = os.path.join(self.backup_dir, backup_type)
                if os.path.exists(backup_path):
                    for file in os.listdir(backup_path):
                        file_path = os.path.join(backup_path, file)
                        if os.path.isfile(file_path):
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_time < cutoff_date:
                                os.remove(file_path)
                                logger.info(f"Deleted old backup: {file_path}")
            
            logger.info(f"Old backups cleanup completed (older than {days} days)")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
            return False
    
    def restore_backup(self, backup_file, backup_type="database"):
        """استعادة نسخة احتياطية"""
        try:
            if backup_type == "database":
                shutil.copy2(backup_file, "data/bot_database.db")
                logger.info(f"Database restored from: {backup_file}")
            elif backup_type == "config":
                # استعادة الإعدادات
                pass
            
            return True
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def notify_admin_backup(self, backup_file):
        try:
            bot = config.telegram.Bot
            file_size = os.path.getsize(backup_file) / (1024 * 1024)

            message = f"""
    🔄 **نسخ احتياطي مكتمل**

    📁 الملف: `{os.path.basename(backup_file)}`
    💾 الحجم: {file_size:.2f} MB
    📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    ✅ الحالة: مكتمل بنجاح
            """

            bot.send_message(
                chat_id=config.telegram.ADMIN_TELEGRAM_ID,
                text=message,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error sending backup notification: {e}")
    
    def start_scheduled_backups(self):
        """بدء النسخ الاحتياطي المجدول"""
        try:
            # نسخ يومي عند 3 صباحاً
            schedule.every().day.at("03:00").do(self.create_full_backup)
            
            # تنظيف أسبوعي للنسخ القديمة
            schedule.every().sunday.at("04:00").do(lambda: self.cleanup_old_backups(7))
            
            # نسخ شهري
            schedule.every(30).days.do(lambda: self.create_full_backup)
            
            logger.info("Scheduled backups started")
            
            # تشغيل المجدول في خيط منفصل
            def run_scheduler():
                while True:
                    schedule.run_pending()
                    time.sleep(5)
            
            threading.Thread(target=run_scheduler, daemon=True).start()
            
            return True
        except Exception as e:
            logger.error(f"Error starting scheduled backups: {e}")
            return False
    
    def get_backup_stats(self):
        """الحصول على إحصائيات النسخ الاحتياطي"""
        try:
            stats = {
                "total_backups": 0,
                "total_size_mb": 0,
                "daily_count": 0,
                "weekly_count": 0,
                "monthly_count": 0,
                "oldest_backup": None,
                "newest_backup": None
            }
            
            for backup_type in ["daily", "weekly", "monthly"]:
                backup_path = os.path.join(self.backup_dir, backup_type)
                if os.path.exists(backup_path):
                    for file in os.listdir(backup_path):
                        if file.endswith(('.zip', '.db')):
                            file_path = os.path.join(backup_path, file)
                            file_size = os.path.getsize(file_path)
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            stats["total_backups"] += 1
                            stats["total_size_mb"] += file_size / (1024 * 1024)
                            stats[f"{backup_type}_count"] += 1
                            
                            if not stats["oldest_backup"] or file_time < stats["oldest_backup"]:
                                stats["oldest_backup"] = file_time
                            
                            if not stats["newest_backup"] or file_time > stats["newest_backup"]:
                                stats["newest_backup"] = file_time
            
            return stats
        except Exception as e:
            logger.error(f"Error getting backup stats: {e}")
            return {}

# إنشاء نسخة عالمية
backup_system = BackupSystem()

def initialize_backup_system():
    """تهيئة نظام النسخ الاحتياطي"""
    backup_system.start_scheduled_backups()
    logger.info("Backup system initialized and scheduled")