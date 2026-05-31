"""
نظام المراقبة والتنبيهات 24/7 (نسخة مستقرة)
"""

import logging
import psutil
import socket
import requests
import time
import os
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, Application

import config.telegram

logger = logging.getLogger(__name__)


class MonitoringSystem:
    """نظام المراقبة المستقر"""

    alerts_sent = {}

    # =========================
    # تشغيل النظام
    # =========================
    @staticmethod
    def start_monitoring(application: Application):
        """تشغيل المراقبة عبر JobQueue"""

        job_queue = application.job_queue

        # مراقبة الأداء كل 5 دقائق
        job_queue.run_repeating(
            MonitoringSystem.monitor_performance,
            interval=300,
            first=10
        )

        # مراقبة الاتصال كل دقيقة
        job_queue.run_repeating(
            MonitoringSystem.monitor_connections,
            interval=60,
            first=5
        )

        # مراقبة السجلات كل 10 دقائق
        job_queue.run_repeating(
            MonitoringSystem.monitor_logs,
            interval=600,
            first=15
        )

        logger.info("Monitoring system started (JobQueue mode)")

    # =========================
    # مراقبة الأداء
    # =========================
    @staticmethod
    async def monitor_performance(context: ContextTypes.DEFAULT_TYPE):
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            logger.debug(
                f"CPU: {cpu}% | RAM: {memory.percent}% | DISK: {disk.percent}%"
            )

            if cpu > 80 and 'cpu' not in MonitoringSystem.alerts_sent:
                await MonitoringSystem.send_alert(context, f"🚨 CPU عالي: {cpu}%")
                MonitoringSystem.alerts_sent['cpu'] = datetime.now()

            if memory.percent > 85 and 'memory' not in MonitoringSystem.alerts_sent:
                await MonitoringSystem.send_alert(context, f"🚨 RAM عالي: {memory.percent}%")
                MonitoringSystem.alerts_sent['memory'] = datetime.now()

            if disk.percent > 90 and 'disk' not in MonitoringSystem.alerts_sent:
                await MonitoringSystem.send_alert(context, f"🚨 القرص ممتلئ: {disk.percent}%")
                MonitoringSystem.alerts_sent['disk'] = datetime.now()

            MonitoringSystem.clean_old_alerts()

        except Exception as e:
            logger.error(f"monitor_performance error: {e}")

    # =========================
    # مراقبة الاتصال
    # =========================
    @staticmethod
    async def monitor_connections(context: ContextTypes.DEFAULT_TYPE):
        try:
            try:
                requests.get("https://api.telegram.org", timeout=5)
                internet = True
            except:
                internet = False

                if 'internet' not in MonitoringSystem.alerts_sent:
                    await MonitoringSystem.send_alert(context, "🚨 انقطاع الإنترنت")
                    MonitoringSystem.alerts_sent['internet'] = datetime.now()

            # فحص بسيط للمنافذ
            ports = [80, 443]

            for port in ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", port))
                sock.close()

        except Exception as e:
            logger.error(f"monitor_connections error: {e}")

    # =========================
    # مراقبة السجلات
    # =========================
    @staticmethod
    async def monitor_logs(context: ContextTypes.DEFAULT_TYPE):
        try:
            log_file = "logs/bot.log"

            if not os.path.exists(log_file):
                return

            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-100:]

            errors = sum(1 for l in lines if "ERROR" in l)

            if errors > 10 and 'errors' not in MonitoringSystem.alerts_sent:
                await MonitoringSystem.send_alert(
                    context,
                    f"🚨 أخطاء كثيرة: {errors}"
                )
                MonitoringSystem.alerts_sent['errors'] = datetime.now()

        except Exception as e:
            logger.error(f"monitor_logs error: {e}")

    # =========================
    # إرسال تنبيه
    # =========================
    @staticmethod
    async def send_alert(context: ContextTypes.DEFAULT_TYPE, message: str):
        try:
            admin_id = config.telegram.ADMIN_TELEGRAM_ID

            text = f"""
🚨 تنبيه النظام

{message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            await context.bot.send_message(
                chat_id=admin_id,
                text=text
            )

        except Exception as e:
            logger.error(f"send_alert error: {e}")

    # =========================
    # تنظيف التنبيهات
    # =========================
    @staticmethod
    def clean_old_alerts():
        now = datetime.now()
        for key in list(MonitoringSystem.alerts_sent.keys()):
            if now - MonitoringSystem.alerts_sent[key] > timedelta(hours=1):
                del MonitoringSystem.alerts_sent[key]

    # =========================
    # حالة النظام
    # =========================
    @staticmethod
    async def system_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            internet = "✅" if MonitoringSystem.check_internet() else "❌"

            msg = f"""
🖥️ حالة النظام

CPU: {cpu}%
RAM: {mem.percent}%
DISK: {disk.percent}%

Internet: {internet}
Uptime: {MonitoringSystem.get_uptime()}
"""

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"status error: {e}")

    # =========================
    # أدوات مساعدة
    # =========================
    @staticmethod
    def check_internet():
        try:
            requests.get("https://api.telegram.org", timeout=3)
            return True
        except:
            return False

    @staticmethod
    def get_uptime():
        try:
            seconds = time.time() - psutil.boot_time()
            return f"{int(seconds//3600)}h"
        except:
            return "?"