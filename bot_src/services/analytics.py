# handlers/analytics.py
import logging
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class AnalyticsSystem:
    """نظام التحليلات والإحصاءات"""
    
    def __init__(self):
        self.data_file = "analytics_data.json"
        self.load_data()
    
    def load_data(self):
        """تحميل بيانات التحليلات"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    # تحويل المجموعات من قوائم (بعد التحميل من JSON) إلى مجموعات فعلية
                    self._convert_sets()
            else:
                self.data = {
                    "users": {},
                    "transactions": {},
                    "commands": {},
                    "sessions": {},
                    "daily_stats": {}
                }
                self.save_data()
        except Exception as e:
            logger.error(f"Error loading analytics data: {e}")
            self.data = {
                "users": {},
                "transactions": {},
                "commands": {},
                "sessions": {},
                "daily_stats": {}
            }
    
    def _convert_sets(self):
        """تحويل القوائم المخزنة في JSON إلى مجموعات (sets)"""
        try:
            # تحويل مجموعات المستخدمين في الأوامر
            for command, data in self.data.get("commands", {}).items():
                if "users" in data and isinstance(data["users"], list):
                    data["users"] = set(data["users"])
            
            # تحويل مجموعات المستخدمين النشطين في الإحصائيات اليومية
            for date, stats in self.data.get("daily_stats", {}).items():
                if "active_users" in stats and isinstance(stats["active_users"], list):
                    stats["active_users"] = set(stats["active_users"])
        except Exception as e:
            logger.error(f"Error converting sets: {e}")
    
    def _prepare_for_save(self, data):
        """تحضير البيانات للحفظ في JSON (تحويل المجموعات إلى قوائم)"""
        if isinstance(data, dict):
            return {k: self._prepare_for_save(v) for k, v in data.items()}
        elif isinstance(data, set):
            return list(data)
        elif isinstance(data, (list, tuple)):
            return [self._prepare_for_save(item) for item in data]
        else:
            return data
    
    def save_data(self):
        """حفظ بيانات التحليلات"""
        try:
            # تحويل المجموعات إلى قوائم قبل الحفظ
            data_to_save = self._prepare_for_save(self.data)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")
    
    def track_user_activity(self, user_id: int, username: str, action: str, details: dict = None):
        """تتبع نشاط المستخدم"""
        try:
            user_id_str = str(user_id)
            today = datetime.now().strftime("%Y-%m-%d")
            
            # تحديث معلومات المستخدم
            if user_id_str not in self.data["users"]:
                self.data["users"][user_id_str] = {
                    "username": username,
                    "first_seen": today,
                    "last_seen": today,
                    "total_actions": 0,
                    "actions_today": 0,
                    "sessions": 0
                }
            else:
                self.data["users"][user_id_str]["last_seen"] = today
                if self.data["users"][user_id_str].get("last_action_date") != today:
                    self.data["users"][user_id_str]["actions_today"] = 0
            
            self.data["users"][user_id_str]["total_actions"] += 1
            self.data["users"][user_id_str]["actions_today"] += 1
            self.data["users"][user_id_str]["last_action_date"] = today
            
            # تتبع الأوامر
            if action.startswith('/'):
                if action not in self.data["commands"]:
                    self.data["commands"][action] = {"count": 0, "users": set()}
                self.data["commands"][action]["count"] += 1
                self.data["commands"][action]["users"].add(user_id_str)
            
            # تحديث الإحصائيات اليومية
            if today not in self.data["daily_stats"]:
                self.data["daily_stats"][today] = {
                    "total_users": 0,
                    "total_actions": 0,
                    "new_users": 0,
                    "active_users": set()
                }
            
            self.data["daily_stats"][today]["active_users"].add(user_id_str)
            self.data["daily_stats"][today]["total_actions"] += 1
            self.data["daily_stats"][today]["total_users"] = len(self.data["daily_stats"][today]["active_users"])
            
            # إذا كان أول ظهور للمستخدم اليوم
            last_seen = self.data["users"][user_id_str].get("last_seen")
            if last_seen != today:
                self.data["daily_stats"][today]["new_users"] += 1
            
            self.save_data()
            return True
        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")
            return False
    
    def track_transaction(self, transaction_type: str, amount: float, user_id: int, status: str):
        """تتبع المعاملات المالية"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            transaction_id = f"{today}_{len(self.data['transactions'])}"
            
            self.data["transactions"][transaction_id] = {
                "type": transaction_type,
                "amount": amount,
                "user_id": user_id,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "date": today
            }
            
            self.save_data()
            return transaction_id
        except Exception as e:
            logger.error(f"Error tracking transaction: {e}")
            return None
    
    def get_daily_stats(self, date: str = None):
        """الحصول على إحصائيات يومية"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date in self.data["daily_stats"]:
            stats = self.data["daily_stats"][date].copy()
            # تحويل set إلى int (عدد العناصر)
            if isinstance(stats.get("active_users"), set):
                stats["active_users"] = len(stats["active_users"])
            elif isinstance(stats.get("active_users"), list):
                stats["active_users"] = len(stats["active_users"])
            else:
                stats["active_users"] = 0
            return stats
        return {
            "total_users": 0,
            "total_actions": 0,
            "new_users": 0,
            "active_users": 0
        }
    
    def get_user_stats(self, user_id: int):
        """الحصول على إحصائيات مستخدم محدد"""
        user_id_str = str(user_id)
        if user_id_str in self.data["users"]:
            return self.data["users"][user_id_str]
        return None
    
    def get_top_users(self, limit: int = 10):
        """الحصول على أكثر المستخدمين نشاطاً"""
        users = []
        for user_id, user_data in self.data["users"].items():
            users.append({
                "user_id": user_id,
                "username": user_data.get("username", "Unknown"),
                "total_actions": user_data.get("total_actions", 0),
                "last_seen": user_data.get("last_seen", "Never")
            })
        
        users.sort(key=lambda x: x["total_actions"], reverse=True)
        return users[:limit]
    
    def get_most_used_commands(self, limit: int = 10):
        """الحصول على أكثر الأوامر استخداماً"""
        commands = []
        for command, data in self.data["commands"].items():
            # حساب عدد المستخدمين الفريدين
            unique_users = 0
            if "users" in data:
                if isinstance(data["users"], set):
                    unique_users = len(data["users"])
                elif isinstance(data["users"], list):
                    unique_users = len(data["users"])
            
            commands.append({
                "command": command,
                "count": data.get("count", 0),
                "unique_users": unique_users
            })
        
        commands.sort(key=lambda x: x["count"], reverse=True)
        return commands[:limit]
    
    def generate_chart(self, data_type: str = "daily_users"):
        """إنشاء مخطط بياني"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if data_type == "daily_users":
                # جمع بيانات 7 أيام الأخيرة
                dates = []
                active_users = []
                new_users = []
                
                for i in range(7):
                    date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                    dates.append(date)
                    stats = self.get_daily_stats(date)
                    active_users.append(stats["active_users"])
                    new_users.append(stats["new_users"])
                
                dates.reverse()
                active_users.reverse()
                new_users.reverse()
                
                ax.bar(dates, active_users, label='Active Users', alpha=0.8)
                ax.bar(dates, new_users, label='New Users', alpha=0.6)
                ax.set_title('User Activity (Last 7 Days)')
                ax.set_xlabel('Date')
                ax.set_ylabel('Number of Users')
                ax.legend()
                ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            chart_path = f"analytics_chart_{data_type}.png"
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            return chart_path
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None

# إنشاء كائن التحليلات العالمي
analytics_system = AnalyticsSystem()


async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /analytics"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        # تتبع النشاط
        analytics_system.track_user_activity(user_id, username, '/analytics')
        
        keyboard = [
            [InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data="analytics_users")],
            [InlineKeyboardButton("📈 أكثر الأوامر استخداماً", callback_data="analytics_commands")],
            [InlineKeyboardButton("👥 أفضل 10 مستخدمين", callback_data="analytics_top_users")],
            [InlineKeyboardButton("📅 إحصائيات اليوم", callback_data="analytics_today")],
            [InlineKeyboardButton("📊 مخطط النشاط", callback_data="analytics_chart")],
            [InlineKeyboardButton("🔄 تحديث البيانات", callback_data="analytics_refresh")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 **مركز التحليلات والإحصائيات**\n\n"
            "اختر نوع التقرير الذي تريده:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in analytics_command: {e}")
        await update.message.reply_text("❌ حدث خطأ في تحميل التحليلات.")


async def analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج ردود الاتصال للتحليلات"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    try:
        if callback_data == "analytics_users":
            # إحصائيات المستخدمين
            total_users = len(analytics_system.data["users"])
            today_stats = analytics_system.get_daily_stats()
            
            message = (
                "👥 **إحصائيات المستخدمين**\n\n"
                f"• إجمالي المستخدمين: {total_users}\n"
                f"• المستخدمون النشطون اليوم: {today_stats['active_users']}\n"
                f"• المستخدمون الجدد اليوم: {today_stats['new_users']}\n"
                f"• إجمالي النشاط اليوم: {today_stats['total_actions']} عملية\n"
                f"• متوسط النشاط/مستخدم: {today_stats['total_actions'] / max(1, today_stats['active_users']):.1f}"
            )
            
        elif callback_data == "analytics_commands":
            # أكثر الأوامر استخداماً
            top_commands = analytics_system.get_most_used_commands(10)
            
            message = "📈 **أكثر الأوامر استخداماً**\n\n"
            for i, cmd in enumerate(top_commands, 1):
                message += f"{i}. `{cmd['command']}` - {cmd['count']} استخدام ({cmd['unique_users']} مستخدم)\n"
            
        elif callback_data == "analytics_top_users":
            # أفضل 10 مستخدمين
            top_users = analytics_system.get_top_users(10)
            
            message = "👑 **أفضل 10 مستخدمين حسب النشاط**\n\n"
            for i, user in enumerate(top_users, 1):
                username_display = f"@{user['username']}" if user['username'] != 'Unknown' else "مستخدم"
                message += f"{i}. {username_display} - {user['total_actions']} عملية\n"
            
        elif callback_data == "analytics_today":
            # إحصائيات اليوم التفصيلية
            today = datetime.now().strftime("%Y-%m-%d")
            today_stats = analytics_system.get_daily_stats()
            
            message = (
                f"📅 **إحصائيات اليوم ({today})**\n\n"
                f"• إجمالي المستخدمين: {today_stats['total_users']}\n"
                f"• المستخدمون الجدد: {today_stats['new_users']}\n"
                f"• إجمالي العمليات: {today_stats['total_actions']}\n"
                f"• متوسط العمليات/مستخدم: {today_stats['total_actions'] / max(1, today_stats['active_users']):.1f}\n\n"
                "📊 **العمليات في الساعات الأخيرة:**\n"
            )
            
            # حساب النشاط في الساعات الأخيرة
            hourly_data = defaultdict(int)
            current_hour = datetime.now().hour
            
            for i in range(24):
                hour = (current_hour - i) % 24
                hourly_data[hour] = 0
            
            for user_data in analytics_system.data["users"].values():
                if user_data.get("last_action_date") == today:
                    # يمكن إضافة تحليل أكثر تفصيلاً هنا
                    pass
            
        elif callback_data == "analytics_chart":
            # إنشاء وإرسال مخطط
            chart_path = analytics_system.generate_chart("daily_users")
            
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as chart_file:
                    await query.message.reply_photo(
                        photo=chart_file,
                        caption="📊 **مخطط نشاط المستخدمين (آخر 7 أيام)**\n\n"
                                "يشير الرسم البياني إلى عدد المستخدمين النشطين والمستخدمين الجدد يومياً."
                    )
                os.remove(chart_path)  # حذف الملف بعد الإرسال
                return
            else:
                message = "❌ تعذر إنشاء المخطط. تأكد من وجود بيانات كافية."
            
        elif callback_data == "analytics_refresh":
            # تحديث البيانات
            analytics_system.load_data()
            message = "✅ تم تحديث بيانات التحليلات بنجاح!"
        
        else:
            message = "❌ خيار غير صالح."
        
        # إعادة إنشاء لوحة المفاتيح
        keyboard = [
            [InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data="analytics_users")],
            [InlineKeyboardButton("📈 أكثر الأوامر استخداماً", callback_data="analytics_commands")],
            [InlineKeyboardButton("👥 أفضل 10 مستخدمين", callback_data="analytics_top_users")],
            [InlineKeyboardButton("📅 إحصائيات اليوم", callback_data="analytics_today")],
            [InlineKeyboardButton("📊 مخطط النشاط", callback_data="analytics_chart")],
            [InlineKeyboardButton("🔄 تحديث البيانات", callback_data="analytics_refresh")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in analytics_callback: {e}")
        await query.edit_message_text("❌ حدث خطأ في تحميل البيانات.")


async def admin_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر التحليلات المتقدم للأدمن"""
    try:
        user_id = update.effective_user.id
        
        # التحقق من صلاحيات الأدمن (يمكنك تعديل هذا الجزء)
        # if user_id not in config.ADMIN_IDS:
        #     await update.message.reply_text("❌ هذا الأمر متاح للإدارة فقط.")
        #     return
        
        keyboard = [
            [InlineKeyboardButton("📊 تقرير شامل", callback_data="admin_analytics_full")],
            [InlineKeyboardButton("📈 أداء البوت", callback_data="admin_analytics_performance")],
            [InlineKeyboardButton("💼 تقرير مالي", callback_data="admin_analytics_financial")],
            [InlineKeyboardButton("📥 تصدير البيانات", callback_data="admin_analytics_export")],
            [InlineKeyboardButton("🧹 تنظيف البيانات", callback_data="admin_analytics_cleanup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **مركز تحليلات الإدارة**\n\n"
            "أدوات متقدمة لتحليل أداء البوت:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in admin_analytics_command: {e}")
        await update.message.reply_text("❌ حدث خطأ في تحميل أدوات الإدارة.")