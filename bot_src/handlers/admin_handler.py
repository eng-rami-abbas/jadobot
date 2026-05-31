# admin_handler.py
"""
معالج صلاحيات الإدمن
"""

import logging
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

import store
import config.telegram
from utils import helpers
from services.iChancyAPI import iChancyAPI
import trans

import supabase_integration as supa

logger = logging.getLogger(__name__)

# نظام التحليلات
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
    
    def save_data(self):
        """حفظ بيانات التحليلات"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")
    
    def track_user_activity(self, user_id: int, username: str, action: str, details: dict = None):
        """تتبع نشاط المستخدم"""
        try:
            user_id_str = str(user_id)
            today = datetime.now().strftime("%Y-%m-%d")
            
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
            
            if action.startswith('/'):
                if action not in self.data["commands"]:
                    self.data["commands"][action] = {"count": 0, "users": set()}
                self.data["commands"][action]["count"] += 1
                self.data["commands"][action]["users"].add(user_id_str)
            
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
            
            last_seen = self.data["users"][user_id_str].get("last_seen")
            if last_seen != today:
                self.data["daily_stats"][today]["new_users"] += 1
            
            self.save_data()
            return True
        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")
            return False
    
    def get_daily_stats(self, date: str = None):
        """الحصول على إحصائيات يومية"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date in self.data["daily_stats"]:
            stats = self.data["daily_stats"][date].copy()
            stats["active_users"] = len(stats["active_users"])
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
            commands.append({
                "command": command,
                "count": data["count"],
                "unique_users": len(data["users"])
            })
        
        commands.sort(key=lambda x: x["count"], reverse=True)
        return commands[:limit]
    
    def generate_chart(self, data_type: str = "daily_users"):
        """إنشاء مخطط بياني"""
        if not MATPLOTLIB_AVAILABLE:
            return None
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if data_type == "daily_users":
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

analytics_system = AnalyticsSystem()

class AdminHandler:
    """فئة معالج صلاحيات الإدمن"""
    
    BOT_STATUS = True
    MAINTENANCE_MESSAGE = "🔧 البوت في حالة صيانة مؤقتة. نعتذر للإزعاج وسنعود قريباً!"
    JACKPOT_WINNERS = []
    
    @staticmethod
    def is_admin(user_id: str) -> bool:
        try:
            admin_id = int(config.telegram.ADMIN_TELEGRAM_ID)
            return str(user_id) == str(admin_id)
        except:
            return str(user_id) == str(config.telegram.ADMIN_TELEGRAM_ID)
    
    @staticmethod
    def user_management_menu():
        keyboard = [
            [
                InlineKeyboardButton("💰 إضافة رصيد", callback_data="admin_add_balance"),
                InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct_balance")
            ],
            [
                InlineKeyboardButton("ℹ️ معلومات مستخدم", callback_data="admin_user_info"),
                InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user")
            ],
            [
                InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data="admin_user_stats"),
                InlineKeyboardButton("📧 إرسال رسالة جماعية", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton("🔙 العودة للوحة الإدمن", callback_data="admin_panel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pending_transactions_menu():
        keyboard = [
            [
                InlineKeyboardButton("✅ الموافقة على معاملة", callback_data="admin_approve_transaction"),
                InlineKeyboardButton("❌ رفض معاملة", callback_data="admin_reject_transaction")
            ],
            [
                InlineKeyboardButton("📊 عرض جميع المعاملات المعلقة", callback_data="admin_view_pending")
            ],
            [
                InlineKeyboardButton("🔙 العودة للوحة الإدمن", callback_data="admin_panel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_back_menu():
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة الإدمن", callback_data="admin_panel")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def cancel_admin_operation():
        keyboard = [
            [
                InlineKeyboardButton("❌ إلغاء العملية", callback_data="cancel_admin_operation"),
                InlineKeyboardButton("🔙 العودة للوحة الإدمن", callback_data="admin_panel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def analytics_menu():
        keyboard = [
            [
                InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data="admin_analytics_users"),
                InlineKeyboardButton("📈 أكثر الأوامر استخداماً", callback_data="admin_analytics_commands")
            ],
            [
                InlineKeyboardButton("👑 أفضل 10 مستخدمين", callback_data="admin_analytics_top_users"),
                InlineKeyboardButton("📅 إحصائيات اليوم", callback_data="admin_analytics_today")
            ],
            [
                InlineKeyboardButton("📉 مخطط النشاط", callback_data="admin_analytics_chart"),
                InlineKeyboardButton("📥 تصدير البيانات", callback_data="admin_analytics_export")
            ],
            [
                InlineKeyboardButton("🔄 تحديث البيانات", callback_data="admin_analytics_refresh"),
                InlineKeyboardButton("🧹 تنظيف البيانات القديمة", callback_data="admin_analytics_cleanup")
            ],
            [
                InlineKeyboardButton("🔙 العودة للوحة الإدمن", callback_data="admin_panel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_panel_menu():
        keyboard = [
            [
                InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users"),
                InlineKeyboardButton("💰 إدارة الأرصدة", callback_data="admin_balance")
            ],
            [
                InlineKeyboardButton("📊 المعاملات المعلقة", callback_data="admin_pending"),
                InlineKeyboardButton("🎁 أكواد الهدايا", callback_data="admin_gifts")
            ],
            [
                InlineKeyboardButton("📢 إرسال إشعار", callback_data="admin_broadcast"),
                InlineKeyboardButton("📈 الإحصائيات والتحليلات", callback_data="admin_analytics")
            ],
            [
                InlineKeyboardButton("⚙️ إعدادات النظام", callback_data="admin_settings"),
                InlineKeyboardButton("📋 سجلات النظام", callback_data="admin_logs")
            ],
            [
                InlineKeyboardButton("🔄 حالة البوت", callback_data="admin_bot_status"),
                InlineKeyboardButton("🎰 إدارة الجاكبوت", callback_data="admin_jackpot")
            ],
            [
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    # ---------- شاشات الإدمن ----------
    @staticmethod
    async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if not AdminHandler.is_admin(user_id):
            await update.callback_query.answer("❌ ليس لديك صلاحية الوصول إلى لوحة الإدمن", show_alert=True)
            return
        
        try:
            today_stats = analytics_system.get_daily_stats()
            total_users = len(analytics_system.data.get("users", {}))
            top_commands = analytics_system.get_most_used_commands(3)
            stats_text = f"""
🔧 **لوحة تحكم الإدمن**

📊 **حالة النظام:**
🤖 حالة البوت: {"🟢 نشط" if AdminHandler.BOT_STATUS else "🔴 متوقف للصيانة"}
👥 إجمالي المستخدمين: {total_users}
📅 المستخدمون النشطون اليوم: {today_stats['active_users']}
🆕 مستخدمون جدد اليوم: {today_stats['new_users']}
📈 إجمالي العمليات اليوم: {today_stats['total_actions']}

🎯 **الأوامر الأكثر استخداماً:**
1. {top_commands[0]['command'] if top_commands else 'لا يوجد'} ({top_commands[0]['count'] if top_commands else 0})
2. {top_commands[1]['command'] if len(top_commands) > 1 else 'لا يوجد'} ({top_commands[1]['count'] if len(top_commands) > 1 else 0})
3. {top_commands[2]['command'] if len(top_commands) > 2 else 'لا يوجد'} ({top_commands[2]['count'] if len(top_commands) > 2 else 0})

اختر العملية المطلوبة من القائمة:
            """
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            stats_text = f"""
🔧 **لوحة تحكم الإدمن**

مرحباً بك في لوحة تحكم الإدمن.
🤖 حالة البوت: {"🟢 نشط" if AdminHandler.BOT_STATUS else "🔴 متوقف للصيانة"}

اختر العملية المطلوبة من القائمة:
            """
        
        # تعديل الرسالة الحالية بدلاً من إنشاء رسالة جديدة
        query = update.callback_query
        try:
            await query.edit_message_text(
                stats_text,
                reply_markup=AdminHandler.admin_panel_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            if "not modified" in str(e).lower():
                pass
            else:
                await query.message.reply_text(
                    stats_text,
                    reply_markup=AdminHandler.admin_panel_menu(),
                    parse_mode='Markdown'
                )
    
    @staticmethod
    async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🤖 إدارة حالة البوت", callback_data="admin_manage_bot_status")],
            [InlineKeyboardButton("🔙 العودة للوحة الإدمن", callback_data="admin_panel")]
        ]
        await update.callback_query.edit_message_text(
            "⚙️ **إعدادات النظام**\n\nاختر الإعداد الذي تريد تعديله:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def manage_bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        current_status = "🟢 نشط" if AdminHandler.BOT_STATUS else "🔴 متوقف للصيانة"
        keyboard = [
            [
                InlineKeyboardButton("🟢 تشغيل البوت", callback_data="admin_bot_start"),
                InlineKeyboardButton("🔴 إيقاف البوت", callback_data="admin_bot_stop")
            ],
            [
                InlineKeyboardButton("📣 إرسال إشعار للمستخدمين", callback_data="admin_send_maintenance_notice")
            ],
            [
                InlineKeyboardButton("🔙 رجوع للإعدادات", callback_data="admin_settings")
            ]
        ]
        await update.callback_query.edit_message_text(
            f"🤖 **إدارة حالة البوت**\n\nالحالة الحالية: {current_status}\n\nاختر العملية:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if AdminHandler.BOT_STATUS:
            await update.callback_query.answer("✅ البوت يعمل بالفعل", show_alert=True)
            return
        AdminHandler.BOT_STATUS = True
        logger.info(f"البوت تم تشغيله بواسطة الإدمن {update.effective_user.id}")
        try:
            await AdminHandler._send_broadcast_message(
                context,
                "🎉 **تم تشغيل البوت**\n\nتم تشغيل البوت بنجاح ويمكنكم استخدامه الآن. نشكر صبركم!"
            )
        except Exception as e:
            logger.error(f"Error sending broadcast: {e}")
        await update.callback_query.answer("✅ تم تشغيل البوت بنجاح", show_alert=True)
        await AdminHandler.manage_bot_status(update, context)
    
    @staticmethod
    async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not AdminHandler.BOT_STATUS:
            await update.callback_query.answer("✅ البوت متوقف بالفعل للصيانة", show_alert=True)
            return
        AdminHandler.BOT_STATUS = False
        logger.info(f"البوت تم إيقافه للصيانة بواسطة الإدمن {update.effective_user.id}")
        try:
            await AdminHandler._send_broadcast_message(
                context,
                f"🔧 **صيانة البوت**\n\n{AdminHandler.MAINTENANCE_MESSAGE}\n\n⏰ التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        except Exception as e:
            logger.error(f"Error sending broadcast: {e}")
        await update.callback_query.answer("✅ تم إيقاف البوت للصيانة بنجاح", show_alert=True)
        await AdminHandler.manage_bot_status(update, context)
    
    @staticmethod
    async def send_maintenance_notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "📣 **إرسال إشعار صيانة**\n\nأرسل رسالة الصيانة التي تريد إرسالها للمستخدمين:\n(يمكنك استخدام التنسيق Markdown)"
        context.user_data['admin_operation'] = 'maintenance_notice'
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='admin_manage_bot_status')]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ---------- إدارة الجاكبوت ----------
    @staticmethod
    async def jackpot_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("➕ إضافة ID فائز", callback_data="admin_add_jackpot_id"),
                InlineKeyboardButton("📋 عرض IDs الفائزين", callback_data="admin_view_jackpot_ids")
            ],
            [
                InlineKeyboardButton("🗑️ حذف ID فائز", callback_data="admin_delete_jackpot_id"),
                InlineKeyboardButton("🔄 مسح الكل", callback_data="admin_clear_jackpot_ids")
            ],
            [
                InlineKeyboardButton("🔙 العودة للوحة الإدمن", callback_data="admin_panel")
            ]
        ]
        winners_count = len(AdminHandler.JACKPOT_WINNERS)
        await update.callback_query.edit_message_text(
            f"🎰 **إدارة الجاكبوت**\n\n📊 **عدد IDs الفائزين:** {winners_count}\n\nاختر العملية المطلوبة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def add_jackpot_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "➕ **إضافة ID فائز جديد**\n\n📝 **أرسل ID الفائز:**"
        context.user_data['admin_operation'] = 'add_jackpot_id'
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='admin_jackpot')]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    @staticmethod
    async def view_jackpot_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not AdminHandler.JACKPOT_WINNERS:
            message = "📋 **لا يوجد IDs فائزين مسجلة بعد**"
        else:
            message = "🏆 **IDs الفائزين بالجاكبوت:**\n\n"
            for i, winner_id in enumerate(AdminHandler.JACKPOT_WINNERS, 1):
                message += f"{i}️⃣ {winner_id}\n"
        keyboard = [
            [InlineKeyboardButton("➕ إضافة ID", callback_data="admin_add_jackpot_id"),
             InlineKeyboardButton("🗑️ حذف ID", callback_data="admin_delete_jackpot_id")],
            [InlineKeyboardButton("🔄 مسح الكل", callback_data="admin_clear_jackpot_ids"),
             InlineKeyboardButton("🔄 تحديث القائمة", callback_data="admin_view_jackpot_ids")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_jackpot")]
        ]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    @staticmethod
    async def delete_jackpot_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not AdminHandler.JACKPOT_WINNERS:
            await update.callback_query.answer("❌ لا يوجد IDs لحذفها", show_alert=True)
            await AdminHandler.jackpot_management(update, context)
            return
        message = "🗑️ **حذف ID فائز**\n\nأرسل **رقم الـ ID** الذي تريد حذفه:\n\n"
        for i, winner_id in enumerate(AdminHandler.JACKPOT_WINNERS, 1):
            message += f"{i}️⃣ {winner_id}\n"
        context.user_data['admin_operation'] = 'delete_jackpot_id'
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='admin_jackpot')]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    @staticmethod
    async def clear_jackpot_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("✅ نعم، مسح الكل", callback_data="admin_confirm_clear_ids"),
             InlineKeyboardButton("❌ لا، إلغاء", callback_data="admin_jackpot")]
        ]
        await update.callback_query.edit_message_text(
            "⚠️ **هل أنت متأكد من مسح جميع IDs الفائزين؟**\n\nهذه العملية لا يمكن التراجع عنها!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def confirm_clear_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
        AdminHandler.JACKPOT_WINNERS = []
        await update.callback_query.answer("✅ تم مسح جميع IDs الفائزين", show_alert=True)
        await AdminHandler.jackpot_management(update, context)
    
    # ---------- إدارة المستخدمين والمعاملات ----------
    @staticmethod
    async def user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.edit_message_text(
            "👥 **إدارة المستخدمين**\n\nاختر العملية المطلوبة:",
            reply_markup=AdminHandler.user_management_menu(),
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def view_pending_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            pending = store.get_pending_transactions()
            if not pending:
                message = "✅ **لا توجد معاملات معلقة حالياً**"
            else:
                message = "⏳ **المعاملات المعلقة:**\n\n"
                for i, transaction in enumerate(pending[:10], 1):
                    username = transaction.get('username', 'غير معروف')
                    message += f"{i}. **#{transaction.get('id', '?')}** - {username}\n"
                    message += f"   💰 {transaction.get('amount_syp', 0)} - {transaction.get('type', 'غير محدد')}\n"
                    message += f"   📅 {transaction.get('created_at', 'غير معروف')}\n\n"
            await update.callback_query.edit_message_text(
                message,
                reply_markup=AdminHandler.pending_transactions_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in pending transactions: {e}")
            await update.callback_query.edit_message_text(
                "❌ **حدث خطأ في عرض المعاملات المعلقة**",
                reply_markup=AdminHandler.admin_back_menu(),
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def analytics_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            today_stats = analytics_system.get_daily_stats()
            total_users = len(analytics_system.data["users"])
            top_users = analytics_system.get_top_users(5)
            top_commands = analytics_system.get_most_used_commands(5)
            
            message = "📊 **لوحة التحليلات والإحصاءات**\n\n"
            message += f"📅 **إحصائيات اليوم ({datetime.now().strftime('%Y-%m-%d')}):**\n"
            message += f"• 👥 المستخدمون النشطون: {today_stats['active_users']}\n"
            message += f"• 🆕 مستخدمون جدد: {today_stats['new_users']}\n"
            message += f"• 📈 إجمالي العمليات: {today_stats['total_actions']}\n\n"
            message += f"📋 **إجمالي المستخدمين:** {total_users}\n\n"
            message += "👑 **أفضل 5 مستخدمين حسب النشاط:**\n"
            for i, user in enumerate(top_users, 1):
                username_display = f"@{user['username']}" if user['username'] != 'Unknown' else "مستخدم"
                message += f"{i}. {username_display} - {user['total_actions']} عملية\n"
            message += "\n📈 **أكثر 5 أوامر استخداماً:**\n"
            for i, cmd in enumerate(top_commands, 1):
                message += f"{i}. `{cmd['command']}` - {cmd['count']} استخدام\n"
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in analytics dashboard: {e}")
            await update.callback_query.edit_message_text(
                "❌ **حدث خطأ في تحميل التحليلات**",
                reply_markup=AdminHandler.admin_back_menu(),
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def show_analytics_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            total_users = len(analytics_system.data["users"])
            today_stats = analytics_system.get_daily_stats()
            message = "👥 **إحصائيات المستخدمين**\n\n"
            message += f"📊 **إحصائيات عامة:**\n"
            message += f"• 👥 إجمالي المستخدمين: {total_users}\n"
            message += f"• 📅 المستخدمون النشطون اليوم: {today_stats['active_users']}\n"
            message += f"• 🆕 مستخدمون جدد اليوم: {today_stats['new_users']}\n"
            message += f"• 📈 إجمالي العمليات اليوم: {today_stats['total_actions']}\n"
            message += f"• 📊 متوسط النشاط/مستخدم: {today_stats['total_actions'] / max(1, today_stats['active_users']):.1f}\n\n"
            message += "📅 **نشاط آخر 7 أيام:**\n"
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                stats = analytics_system.get_daily_stats(date)
                message += f"• {date}: {stats['active_users']} نشيط، {stats['new_users']} جديد\n"
            await update.callback_query.edit_message_text(
                message,
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error showing analytics users: {e}")
            await update.callback_query.edit_message_text(
                "❌ حدث خطأ في عرض إحصائيات المستخدمين",
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def show_analytics_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            top_commands = analytics_system.get_most_used_commands(15)
            message = "📈 **أكثر الأوامر استخداماً**\n\n"
            for i, cmd in enumerate(top_commands, 1):
                message += f"{i}. `{cmd['command']}`\n"
                message += f"   • عدد الاستخدامات: {cmd['count']}\n"
                message += f"   • عدد المستخدمين: {cmd['unique_users']}\n"
                message += f"   • متوسط الاستخدام/مستخدم: {cmd['count'] / max(1, cmd['unique_users']):.1f}\n\n"
            await update.callback_query.edit_message_text(
                message,
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error showing analytics commands: {e}")
            await update.callback_query.edit_message_text(
                "❌ حدث خطأ في عرض إحصائيات الأوامر",
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def show_analytics_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            top_users = analytics_system.get_top_users(15)
            message = "👑 **أفضل المستخدمين حسب النشاط**\n\n"
            for i, user in enumerate(top_users, 1):
                username_display = f"@{user['username']}" if user['username'] != 'Unknown' else f"مستخدم {user['user_id']}"
                message += f"{i}. {username_display}\n"
                message += f"   • إجمالي العمليات: {user['total_actions']}\n"
                message += f"   • آخر ظهور: {user['last_seen']}\n\n"
            await update.callback_query.edit_message_text(
                message,
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error showing analytics top users: {e}")
            await update.callback_query.edit_message_text(
                "❌ حدث خطأ في عرض أفضل المستخدمين",
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def show_analytics_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            today_stats = analytics_system.get_daily_stats(today)
            message = f"📅 **إحصائيات اليوم ({today})**\n\n"
            message += f"📊 **النشاط اليومي:**\n"
            message += f"• 👥 المستخدمون النشطون: {today_stats['active_users']}\n"
            message += f"• 🆕 مستخدمون جدد: {today_stats['new_users']}\n"
            message += f"• 📈 إجمالي العمليات: {today_stats['total_actions']}\n"
            message += f"• 📊 متوسط العمليات/مستخدم: {today_stats['total_actions'] / max(1, today_stats['active_users']):.1f}\n\n"
            message += "⏰ **توزيع النشاط (تقريبي):**\n"
            current_hour = datetime.now().hour
            for hour in range(24):
                if hour <= current_hour:
                    message += f"• {hour:02d}:00 - تقدير: {int(today_stats['total_actions'] * 0.05)}\n"
            await update.callback_query.edit_message_text(
                message,
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error showing analytics today: {e}")
            await update.callback_query.edit_message_text(
                "❌ حدث خطأ في عرض إحصائيات اليوم",
                reply_markup=AdminHandler.analytics_menu(),
                parse_mode='Markdown'
            )
    
    @staticmethod
    async def send_analytics_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            chart_path = analytics_system.generate_chart("daily_users")
            if chart_path and os.path.exists(chart_path):
                with open(chart_path, 'rb') as chart_file:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=chart_file,
                        caption="📊 **مخطط نشاط المستخدمين (آخر 7 أيام)**\n\nيشير الرسم البياني إلى عدد المستخدمين النشطين والمستخدمين الجدد يومياً.",
                        reply_markup=AdminHandler.analytics_menu()
                    )
                os.remove(chart_path)
            else:
                await update.callback_query.answer("❌ تعذر إنشاء المخطط. تأكد من وجود بيانات كافية.", show_alert=True)
                await AdminHandler.analytics_dashboard(update, context)
        except Exception as e:
            logger.error(f"Error sending analytics chart: {e}")
            await update.callback_query.answer("❌ حدث خطأ في إنشاء المخطط", show_alert=True)
            await AdminHandler.analytics_dashboard(update, context)
    
    @staticmethod
    async def export_analytics_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            data_file = "analytics_data_export.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(analytics_system.data, f, indent=4, ensure_ascii=False)
            with open(data_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    caption="📥 **تم تصدير بيانات التحليلات**\n\nيحتوي الملف على جميع بيانات التحليلات والإحصائيات.",
                    reply_markup=AdminHandler.analytics_menu()
                )
            os.remove(data_file)
        except Exception as e:
            logger.error(f"Error exporting analytics data: {e}")
            await update.callback_query.answer("❌ حدث خطأ في تصدير البيانات", show_alert=True)
            await AdminHandler.analytics_dashboard(update, context)
    
    @staticmethod
    async def refresh_analytics_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            analytics_system.load_data()
            await update.callback_query.answer("✅ تم تحديث بيانات التحليلات", show_alert=True)
            await AdminHandler.analytics_dashboard(update, context)
        except Exception as e:
            logger.error(f"Error refreshing analytics data: {e}")
            await update.callback_query.answer("❌ حدث خطأ في تحديث البيانات", show_alert=True)
    
    @staticmethod
    async def cleanup_analytics_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            keyboard = [
                [InlineKeyboardButton("🗑️ حذف بيانات قديمة (30+ يوم)", callback_data="admin_analytics_cleanup_confirm"),
                 InlineKeyboardButton("❌ إلغاء", callback_data="admin_analytics")]
            ]
            await update.callback_query.edit_message_text(
                "🧹 **تنظيف بيانات التحليلات القديمة**\n\n⚠️ **تحذير:** هذه العملية ستقوم بحذف جميع البيانات الأقدم من 30 يوم.\n\nهل أنت متأكد من المتابعة؟",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in cleanup analytics data: {e}")
            await update.callback_query.answer("❌ حدث خطأ", show_alert=True)
    
    @staticmethod
    async def confirm_analytics_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            deleted_count = 0
            for date in list(analytics_system.data["daily_stats"].keys()):
                if date < cutoff_date:
                    del analytics_system.data["daily_stats"][date]
                    deleted_count += 1
            analytics_system.save_data()
            await update.callback_query.answer(f"✅ تم حذف {deleted_count} يوم من البيانات القديمة", show_alert=True)
            await AdminHandler.analytics_dashboard(update, context)
        except Exception as e:
            logger.error(f"Error confirming analytics cleanup: {e}")
            await update.callback_query.answer("❌ حدث خطأ في تنظيف البيانات", show_alert=True)
    
    # ---------- أوامر الإدخال ----------
    @staticmethod
    async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "💰 **إضافة رصيد**\n\nأرسل معرف المستخدم والمبلغ بالتنسيق التالي:\n\nمثال: 123456789 100"
        context.user_data['admin_operation'] = 'add_balance'
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='admin_panel')]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    @staticmethod
    async def deduct_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "💸 **خصم رصيد**\n\nأرسل معرف التليجرام والمبلغ بالتنسيق التالي:\nuser_id amount\n\nمثال: 123456789 50"
        context.user_data['admin_operation'] = 'deduct_balance'
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='admin_panel')]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    @staticmethod
    async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "ℹ️ **معلومات المستخدم**\n\nأرسل معرف التليجرام:"
        context.user_data['admin_operation'] = 'user_info'
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='admin_panel')]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    @staticmethod
    async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = "📢 **إرسال رسالة جماعية**\n\nأرسل الرسالة التي تريد إرسالها لجميع المستخدمين:"
        context.user_data['admin_operation'] = 'broadcast'
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='admin_panel')]]
        await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    @staticmethod
    async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        operation = context.user_data.get('admin_operation')
        text = update.message.text.strip()
        
        if operation == 'add_balance':
            await AdminHandler._handle_balance_operation(update, context, text, 'add')
        elif operation == 'deduct_balance':
            await AdminHandler._handle_balance_operation(update, context, text, 'deduct')
        elif operation == 'user_info':
            await AdminHandler._handle_user_info(update, context, text)
        elif operation == 'approve_transaction':
            await AdminHandler._handle_transaction_action(update, context, text, 'approve')
        elif operation == 'reject_transaction':
            await AdminHandler._handle_transaction_action(update, context, text, 'reject')
        elif operation == 'broadcast':
            await AdminHandler._handle_broadcast(update, context, text)
        elif operation == 'maintenance_notice':
            await AdminHandler._handle_maintenance_notice(update, context, text)
        elif operation == 'add_jackpot_id':
            await AdminHandler._handle_add_jackpot_id(update, context, text)
        elif operation == 'delete_jackpot_id':
            await AdminHandler._handle_delete_jackpot_id(update, context, text)
        
        context.user_data.pop('admin_operation', None)
    
    # ---------- دوال المساعدة الداخلية ----------
    @staticmethod
    async def _handle_maintenance_notice(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        try:
            AdminHandler.MAINTENANCE_MESSAGE = text
            await AdminHandler._send_broadcast_message(
                context,
                f"🔔 **إشعار مهم**\n\n{text}\n\n⏰ التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            await update.message.reply_text(
                "✅ تم تحديث رسالة الصيانة وإرسالها للمستخدمين",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]])
            )
        except Exception as e:
            logger.error(f"Error in maintenance notice: {e}")
            await update.message.reply_text("❌ حدث خطأ في إرسال الرسالة",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
    
    @staticmethod
    async def _handle_add_jackpot_id(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        try:
            AdminHandler.JACKPOT_WINNERS.append(text)
            await update.message.reply_text(
                f"✅ **تم إضافة ID الفائز بنجاح!**\n\n🏆 **الـ ID المضاف:** {text}\n📊 **العدد الكلي الآن:** {len(AdminHandler.JACKPOT_WINNERS)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إدارة الجاكبوت", callback_data='admin_jackpot')]])
            )
        except Exception as e:
            logger.error(f"Error adding jackpot ID: {e}")
            await update.message.reply_text(f"❌ **حدث خطأ في إضافة الـ ID:**\n\n{str(e)}",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إدارة الجاكبوت", callback_data='admin_jackpot')]]))
    
    @staticmethod
    async def _handle_delete_jackpot_id(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        try:
            try:
                index = int(text.strip()) - 1
            except ValueError:
                await update.message.reply_text("❌ **رقم الـ ID غير صحيح!**",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إدارة الجاكبوت", callback_data='admin_jackpot')]]))
                return
            if index < 0 or index >= len(AdminHandler.JACKPOT_WINNERS):
                await update.message.reply_text(f"❌ **رقم الـ ID غير موجود!**\n\nالرقم يجب أن يكون بين 1 و {len(AdminHandler.JACKPOT_WINNERS)}",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إدارة الجاكبوت", callback_data='admin_jackpot')]]))
                return
            deleted_id = AdminHandler.JACKPOT_WINNERS.pop(index)
            await update.message.reply_text(
                f"✅ **تم حذف الـ ID بنجاح!**\n\n🏆 **الـ ID المحذوف:** {deleted_id}\n📊 **العدد الكلي الآن:** {len(AdminHandler.JACKPOT_WINNERS)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إدارة الجاكبوت", callback_data='admin_jackpot')]])
            )
        except Exception as e:
            logger.error(f"Error deleting jackpot ID: {e}")
            await update.message.reply_text(f"❌ **حدث خطأ في حذف الـ ID:**\n\n{str(e)}",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إدارة الجاكبوت", callback_data='admin_jackpot')]]))
    
    @staticmethod
    async def _send_broadcast_message(context: ContextTypes.DEFAULT_TYPE, message: str):
        import asyncio
        try:
            users = store.get_all_users()
            if not users:
                logger.warning("لا يوجد مستخدمين لإرسال الرسالة لهم")
                return 0
            successful_sends = 0
            failed_sends = 0
            logger.info(f"إرسال إشعار لـ {len(users)} مستخدم")
            for user in users:
                try:
                    telegram_id = user.get('telegram_id')
                    if telegram_id:
                        sent = False
                        # Try Markdown first, then HTML, then plain text
                        try:
                            await context.bot.send_message(chat_id=int(telegram_id), text=message, parse_mode='Markdown')
                            sent = True
                        except Exception:
                            pass
                        if not sent:
                            try:
                                await context.bot.send_message(chat_id=int(telegram_id), text=message, parse_mode='HTML')
                                sent = True
                            except Exception:
                                pass
                        if not sent:
                            try:
                                # Strip markdown characters and send as plain text
                                import re
                                plain_text = re.sub(r'[\*_\[\]\(\)`~>#]', '', message)
                                await context.bot.send_message(chat_id=int(telegram_id), text=plain_text)
                                sent = True
                            except Exception:
                                pass
                        successful_sends += 1
                        await asyncio.sleep(0.1)
                except Exception as e:
                    failed_sends += 1
                    logger.warning(f"لا يمكن إرسال إشعار للمستخدم {user.get('telegram_id')}: {e}")
            logger.info(f"تم إرسال الإشعار لـ {successful_sends} من {len(users)} مستخدم ({failed_sends} فشل)")
            return successful_sends
        except Exception as e:
            logger.error(f"Error in broadcast message: {e}")
            return 0
    
    @staticmethod
    async def _handle_balance_operation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, operation: str):
        try:
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ تنسيق خاطئ. استخدم: user_id amount",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
                return
            telegram_id = parts[0]
            amount = int(parts[1])
            user = store.getUserByTelegramId(telegram_id)
            if not user:
                await update.message.reply_text("❌ المستخدم غير موجود",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
                return
            current_balance = float(user.get('balance_syp', 0) or 0)
            if operation == 'add':
                new_balance = current_balance + amount
                action, emoji = "إضافة", "➕"
            else:
                if current_balance < amount:
                    await update.message.reply_text(f"❌ رصيد المستخدم غير كافي\n💵 الرصيد الحالي: {current_balance}",
                                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
                    return
                new_balance = current_balance - amount
                action, emoji = "خصم", "➖"
            supa.update_user_balance(telegram_id, new_balance)
            try:
                await context.bot.send_message(chat_id=int(telegram_id), text=f"{emoji} تم {action} {amount} إلى رصيدك\n💵 رصيدك الحالي: {new_balance}")
            except TelegramError as e:
                logger.warning(f"لا يمكن إرسال إشعار للمستخدم {telegram_id}: {e}")
            await update.message.reply_text(
                f"✅ تم {action} {amount} بنجاح\n👤 المستخدم: {user.get('telegram_username', 'غير معروف')}\n💵 الرصيد الجديد: {new_balance}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
        except (ValueError, IndexError) as e:
            logger.error(f"Error in balance operation: {e}")
            await update.message.reply_text("❌ تنسيق خاطئ. استخدم: user_id amount",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
    
    @staticmethod
    async def _handle_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        try:
            telegram_id = text.strip()
            user = store.getUserByTelegramId(telegram_id)
            if not user:
                await update.message.reply_text("❌ المستخدم غير موجود",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
                return
            
            # Get iChancy details
            ichancy_account = supa.get_ichancy_details_by_telegram_id(telegram_id)
            
            message = f"""
👤 معلومات المستخدم

🆔 معرف التليجرام: {user.get('telegram_id', telegram_id)}
👤 اسم المستخدم: {user.get('username', 'غير محدد')}
📧 الاسم الأول: {user.get('first_name', 'غير محدد')}
📅 تاريخ التسجيل: {user.get('created_at', 'غير معروف')}

💰 الأرصدة:
💵 رصيد البوت: {user.get('balance_syp', 0)}

🎮 حساب Ichancy:
{"👤 الاسم: " + ichancy_account.get('username', 'غير محدد') if ichancy_account else "❌ لا يوجد حساب"}
{"🆔 معرف اللاعب: " + str(ichancy_account.get('player_id', 'غير محدد')) if ichancy_account else ""}
            """
            await update.message.reply_text(message,
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
        except Exception as e:
            logger.error(f"Error in user info: {e}")
            await update.message.reply_text("❌ حدث خطأ في عرض معلومات المستخدم",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
    
    @staticmethod
    async def _handle_transaction_action(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, action: str):
        await update.message.reply_text("⚠️ هذه الميزة تحتاج لتعديل ملف transactions.py",
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
    
    @staticmethod
    async def _handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        import asyncio
        try:
            users = store.get_all_users()
            if not users:
                await update.message.reply_text("❌ لا يوجد مستخدمين لإرسال الرسالة لهم",
                                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
                return
            user_count = len(users)
            successful_sends = 0
            failed_sends = 0
            await update.message.reply_text(f"📤 جاري إرسال الرسالة إلى {user_count} مستخدم...")
            broadcast_text = f"📢 رسالة من الإدارة:\n\n{text}"
            for user in users:
                try:
                    telegram_id = user.get('telegram_id')
                    if telegram_id:
                        sent = False
                        # Try Markdown first, then HTML, then plain text
                        try:
                            await context.bot.send_message(chat_id=int(telegram_id), text=broadcast_text, parse_mode='Markdown')
                            sent = True
                        except Exception:
                            pass
                        if not sent:
                            try:
                                await context.bot.send_message(chat_id=int(telegram_id), text=broadcast_text, parse_mode='HTML')
                                sent = True
                            except Exception:
                                pass
                        if not sent:
                            try:
                                import re
                                plain_text = re.sub(r'[\*_\[\]\(\)`~>#]', '', broadcast_text)
                                await context.bot.send_message(chat_id=int(telegram_id), text=plain_text)
                                sent = True
                            except Exception:
                                pass
                        successful_sends += 1
                        await asyncio.sleep(0.1)
                except Exception as e:
                    failed_sends += 1
            report = f"""
✅ **تم إرسال الرسالة الجماعية بنجاح**

📊 **النتائج:**
• ✅ تم الإرسال بنجاح: {successful_sends}
• ❌ فشل في الإرسال: {failed_sends}
• 👥 الإجمالي: {user_count}

📝 **الرسالة المرسلة:**
{text[:200]}...
            """
            await update.message.reply_text(report,
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await update.message.reply_text(f"❌ حدث خطأ في إرسال الرسالة الجماعية:\n\n{str(e)}",
                                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')]]))
    
    # ---------- دوال غير مكتملة ----------
    @staticmethod
    async def _handle_approve_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.answer("قيد التطوير", show_alert=True)
    
    @staticmethod
    async def _handle_reject_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.answer("قيد التطوير", show_alert=True)
    
    # ---------- موزع الأزرار الرئيسي ----------
    @staticmethod
    async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == 'admin_panel':
            await AdminHandler.admin_panel(update, context)
        elif data == 'admin_settings':
            await AdminHandler.admin_settings_menu(update, context)
        elif data == 'admin_manage_bot_status':
            await AdminHandler.manage_bot_status(update, context)
        elif data == 'admin_bot_start':
            await AdminHandler.start_bot(update, context)
        elif data == 'admin_bot_stop':
            await AdminHandler.stop_bot(update, context)
        elif data == 'admin_send_maintenance_notice':
            await AdminHandler.send_maintenance_notice(update, context)
        elif data == 'admin_jackpot':
            await AdminHandler.jackpot_management(update, context)
        elif data == 'admin_add_jackpot_id':
            await AdminHandler.add_jackpot_id(update, context)
        elif data == 'admin_view_jackpot_ids':
            await AdminHandler.view_jackpot_ids(update, context)
        elif data == 'admin_delete_jackpot_id':
            await AdminHandler.delete_jackpot_id(update, context)
        elif data == 'admin_clear_jackpot_ids':
            await AdminHandler.clear_jackpot_ids(update, context)
        elif data == 'admin_confirm_clear_ids':
            await AdminHandler.confirm_clear_ids(update, context)
        elif data == 'admin_users':
            await AdminHandler.user_management(update, context)
        elif data == 'admin_add_balance':
            await AdminHandler.add_balance(update, context)
        elif data == 'admin_deduct_balance':
            await AdminHandler.deduct_balance(update, context)
        elif data == 'admin_user_info':
            await AdminHandler.user_info(update, context)
        elif data == 'admin_pending':
            await AdminHandler.view_pending_transactions(update, context)
        elif data == 'admin_broadcast':
            await AdminHandler.broadcast_message(update, context)
        elif data == 'admin_analytics':
            await AdminHandler.analytics_dashboard(update, context)
        elif data == 'admin_analytics_users':
            await AdminHandler.show_analytics_users(update, context)
        elif data == 'admin_analytics_commands':
            await AdminHandler.show_analytics_commands(update, context)
        elif data == 'admin_analytics_top_users':
            await AdminHandler.show_analytics_top_users(update, context)
        elif data == 'admin_analytics_today':
            await AdminHandler.show_analytics_today(update, context)
        elif data == 'admin_analytics_chart':
            await AdminHandler.send_analytics_chart(update, context)
        elif data == 'admin_analytics_export':
            await AdminHandler.export_analytics_data(update, context)
        elif data == 'admin_analytics_refresh':
            await AdminHandler.refresh_analytics_data(update, context)
        elif data == 'admin_analytics_cleanup':
            await AdminHandler.cleanup_analytics_data(update, context)
        elif data == 'admin_analytics_cleanup_confirm':
            await AdminHandler.confirm_analytics_cleanup(update, context)
        elif data == 'admin_stats':
            await query.edit_message_text("📊 الإحصائيات التفصيلية قيد التطوير",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]]))
        elif data == 'admin_gifts':
            await query.edit_message_text("🎁 إدارة أكواد الهدايا قيد التطوير",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]]))
        elif data == 'admin_users_list':
            await query.edit_message_text("📋 قائمة المستخدمين قيد التطوير",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_users')]]))
        elif data == 'admin_approve':
            await AdminHandler._handle_approve_transaction(update, context)
        elif data == 'admin_reject':
            await AdminHandler._handle_reject_transaction(update, context)
        elif data == 'admin_user_stats':
            await AdminHandler.analytics_dashboard(update, context)
        elif data == 'admin_ban_user':
            await query.answer("⚠️ ميزة حظر المستخدمين قيد التطوير", show_alert=True)
        elif data == 'admin_approve_transaction':
            await AdminHandler._handle_approve_transaction(update, context)
        elif data == 'admin_reject_transaction':
            await AdminHandler._handle_reject_transaction(update, context)
        elif data == 'admin_balance':
            await AdminHandler.user_management(update, context)
        elif data == 'admin_logs':
            try:
                recent = store.get_recent_transactions(10)
                if not recent:
                    msg = "📋 لا توجد سجلات"
                else:
                    msg = "📋 **آخر السجلات:**\n\n"
                    for i, tx in enumerate(recent, 1):
                        msg += f"{i}. {tx.get('type', '?')} - {tx.get('amount_syp', 0)} - {tx.get('status', '?')}\n"
                await query.edit_message_text(msg,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]]),
                    parse_mode='Markdown')
            except Exception as e:
                await query.edit_message_text(f"❌ خطأ في جلب السجلات: {e}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')]]))
        elif data == 'admin_bot_status':
            await AdminHandler.manage_bot_status(update, context)
        elif data == 'cancel_admin_operation':
            context.user_data.pop('admin_operation', None)
            await AdminHandler.admin_panel(update, context)
        else:
            await query.answer("زر غير معروف", show_alert=True)

# دوال مستقلة
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if AdminHandler.is_admin(user_id):
        await AdminHandler.admin_panel(update, context)
    else:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى لوحة الإدمن")

async def handle_admin_button(query, user_id):
    if AdminHandler.is_admin(user_id):
        await AdminHandler.admin_panel(query, None)
    else:
        await query.answer("❌ ليس لديك صلاحية الوصول إلى لوحة الإدمن", show_alert=True)
