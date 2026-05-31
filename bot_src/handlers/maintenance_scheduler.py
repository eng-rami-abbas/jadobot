"""
نظام الصيانة الدورية والنسخ الاحتياطي
"""

import logging
import schedule
import time
import threading
from datetime import datetime
import os
import shutil
from config.telegram import Update
from telegram.ext import ContextTypes

import store
import config.telegram
import handlers.ichancy

logger = logging.getLogger(__name__)

class MaintenanceScheduler:
    """نظام الصيانة الدورية"""
    
    @staticmethod
    def schedule_maintenance():
        """جدولة المهام الدورية"""
        
        # النسخ الاحتياطي اليومي (2:00 صباحاً)
        schedule.every().day.at("02:00").do(MaintenanceScheduler.daily_backup)
        
        # تنظيف السجلات الأسبوعي (الأحد 3:00 صباحاً)
        schedule.every().sunday.at("03:00").do(MaintenanceScheduler.cleanup_logs)
        
        # التحقق من الصحة الشهري (أول يوم من الشهر 4:00 صباحاً)
        schedule.every().day.at("04:00").do(
            MaintenanceScheduler.monthly_health_check
        ).tag("first_day")
        
        logger.info("Maintenance scheduler initialized")
    
    @staticmethod
    def daily_backup():
        """نسخ احتياطي يومي"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"backups/daily/{timestamp}"
            
            # إنشاء مجلد النسخ الاحتياطي
            os.makedirs(backup_dir, exist_ok=True)
            
            # نسخ الملفات المهمة
            important_files = [
                "data/",
                "config/",
                "logs/",
                "store.py",
                "bot.py"
            ]
            
            for file_path in important_files:
                if os.path.exists(file_path):
                    if os.path.isdir(file_path):
                        shutil.copytree(file_path, f"{backup_dir}/{file_path}")
                    else:
                        shutil.copy2(file_path, backup_dir)
            
            # حذف النسخ القديمة (أكثر من 7 أيام)
            MaintenanceScheduler.clean_old_backups("backups/daily/", days=7)
            
            logger.info(f"Daily backup completed: {backup_dir}")
            
        except Exception as e:
            logger.error(f"Daily backup failed: {e}")
    
    @staticmethod
    def cleanup_logs():
        """تنظيف السجلات"""
        try:
            log_dir = "logs/"
            
            if os.path.exists(log_dir):
                # حذف السجلات القديمة (أكثر من 30 يوم)
                for filename in os.listdir(log_dir):
                    file_path = os.path.join(log_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = datetime.now().timestamp() - os.path.getmtime(file_path)
                        if file_age > 30 * 24 * 3600:  # 30 يوم
                            os.remove(file_path)
                            logger.info(f"Deleted old log: {filename}")
            
            # ضغط السجلات الحالية
            current_log = "bot.log"
            if os.path.exists(current_log) and os.path.getsize(current_log) > 10 * 1024 * 1024:  # > 10MB
                shutil.move(current_log, f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log")
            
            logger.info("Log cleanup completed")
            
        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
    
    @staticmethod
    def monthly_health_check():
        """فحص صحة النظام الشهري"""
        try:
            report = []
            
            # فحص قاعدة البيانات
            try:
                # محاولة الاتصال بقاعدة البيانات
                conn = store.getDatabaseConnection()
                if conn:
                    report.append("✅ قاعدة البيانات: نشطة")
                    conn.close()
                else:
                    report.append("❌ قاعدة البيانات: غير متصلة")
            except Exception as e:
                report.append(f"❌ قاعدة البيانات: خطأ - {str(e)}")
            
            # فحص الملفات الأساسية
            essential_files = [
                "bot.py", "store.py", "config/telegram.py", 
                "config/ichancy.py", "config/database.py"
            ]
            
            for file in essential_files:
                if os.path.exists(file):
                    report.append(f"✅ ملف {file}: موجود")
                else:
                    report.append(f"❌ ملف {file}: مفقود")
            
            # فحص المساحة التخزينية
            total, used, free = shutil.disk_usage("/")
            disk_usage = (used / total) * 100
            report.append(f"💾 استخدام القرص: {disk_usage:.1f}%")
            
            # حفظ التقرير
            report_file = f"logs/health_check_{datetime.now().strftime('%Y%m')}.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(f"تقرير فحص الصحة - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n")
                for item in report:
                    f.write(item + "\n")
            
            logger.info(f"Monthly health check completed: {report_file}")
            
        except Exception as e:
            logger.error(f"Monthly health check failed: {e}")
    
    @staticmethod
    def clean_old_backups(backup_dir, days=7):
        """حذف النسخ القديمة"""
        try:
            if not os.path.exists(backup_dir):
                return
            
            cutoff_time = time.time() - (days * 24 * 3600)
            
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                if os.path.isdir(item_path):
                    item_time = os.path.getmtime(item_path)
                    if item_time < cutoff_time:
                        shutil.rmtree(item_path)
                        logger.info(f"Deleted old backup: {item_path}")
                        
        except Exception as e:
            logger.error(f"Failed to clean old backups: {e}")
    
    @staticmethod
    def run_scheduler():
        """تشغيل المجدول في خيط منفصل"""
        def scheduler_loop():
            while True:
                schedule.run_pending()
                time.sleep(60)  # التحقق كل دقيقة
        
        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()
        logger.info("Maintenance scheduler thread started")