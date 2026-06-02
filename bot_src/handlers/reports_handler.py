"""
نظام التقارير والإحصائيات المتقدم
"""

import logging
from datetime import datetime, timedelta
from config.telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import store
import config.telegram
import helpers

logger = logging.getLogger(__name__)

class ReportsHandler:
    """معالج التقارير والإحصائيات"""
    
    @staticmethod
    async def show_reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة التقارير"""
        user_id = str(update.effective_user.id)
        
        # التحقق من صلاحية الإدمن
        try:
            admin_id = str(config.telegram.ADMIN_TELEGRAM_ID)
            if user_id != admin_id:
                await update.callback_query.answer("❌ ليس لديك صلاحية الوصول", show_alert=True)
                return
        except:
            await update.callback_query.answer("❌ ليس لديك صلاحية الوصول", show_alert=True)
            return
        
        message = """
📊 **نظام التقارير المتقدم**

اختر نوع التقرير المطلوب:
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📈 تقرير مالي", callback_data='report_financial'),
                InlineKeyboardButton("👥 تقرير المستخدمين", callback_data='report_users')
            ],
            [
                InlineKeyboardButton("💸 تقرير المعاملات", callback_data='report_transactions'),
                InlineKeyboardButton("🎁 تقرير الهدايا", callback_data='report_gifts')
            ],
            [
                InlineKeyboardButton("💰 تقرير الإحالات", callback_data='report_referrals'),
                InlineKeyboardButton("⏰ تقرير النشاط", callback_data='report_activity')
            ],
            [
                InlineKeyboardButton("📥 تصدير CSV", callback_data='export_csv'),
                InlineKeyboardButton("📊 إحصائيات فورية", callback_data='live_stats')
            ],
            [
                InlineKeyboardButton("🔙 لوحة الإدمن", callback_data='admin_panel')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @staticmethod
    def generate_financial_report():
        """توليد تقرير مالي"""
        try:
            # بيانات افتراضية - تحتاج لتعديل مع قاعدة البيانات الحقيقية
            report = {
                "total_deposits": 0,
                "total_withdrawals": 0,
                "total_balance": 0,
                "today_deposits": 0,
                "today_withdrawals": 0,
                "avg_deposit": 0,
                "avg_withdrawal": 0,
                "top_deposits": [],
                "top_withdrawals": []
            }
            
            # هنا يمكنك إضافة كود لجلب البيانات الحقيقية من قاعدة البيانات
            
            return report
        except Exception as e:
            logger.error(f"Error generating financial report: {e}")
            return {}
    
    @staticmethod
    def generate_users_report():
        """توليد تقرير المستخدمين"""
        try:
            report = {
                "total_users": 0,
                "active_today": 0,
                "active_week": 0,
                "active_month": 0,
                "new_today": 0,
                "new_week": 0,
                "new_month": 0,
                "top_referrers": [],
                "top_balances": []
            }
            
            return report
        except Exception as e:
            logger.error(f"Error generating users report: {e}")
            return {}
    
    @staticmethod
    def format_report(report_data, report_type):
        """تنسيق التقرير للعرض"""
        if report_type == "financial":
            message = f"""
📈 **التقرير المالي الشامل**

💰 **الإيداعات:**
• الإجمالي: {helpers.format_currency(report_data.get('total_deposits', 0))}
• اليوم: {helpers.format_currency(report_data.get('today_deposits', 0))}
• المتوسط: {helpers.format_currency(report_data.get('avg_deposit', 0))}

💸 **السحوبات:**
• الإجمالي: {helpers.format_currency(report_data.get('total_withdrawals', 0))}
• اليوم: {helpers.format_currency(report_data.get('today_withdrawals', 0))}
• المتوسط: {helpers.format_currency(report_data.get('avg_withdrawal', 0))}

💵 **الأرصدة:**
• إجمالي الأرصدة: {helpers.format_currency(report_data.get('total_balance', 0))}

📅 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """
        
        elif report_type == "users":
            message = f"""
👥 **تقرير المستخدمين**

📊 **الإحصائيات:**
• إجمالي المستخدمين: {report_data.get('total_users', 0)}
• نشطون اليوم: {report_data.get('active_today', 0)}
• نشطون هذا الأسبوع: {report_data.get('active_week', 0)}
• نشطون هذا الشهر: {report_data.get('active_month', 0)}

🆕 **مستخدمون جدد:**
• اليوم: {report_data.get('new_today', 0)}
• هذا الأسبوع: {report_data.get('new_week', 0)}
• هذا الشهر: {report_data.get('new_month', 0)}

📅 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """
        
        return message
    
    @staticmethod
    async def handle_reports_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استدعاءات التقارير"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'report_financial':
            report = ReportsHandler.generate_financial_report()
            message = ReportsHandler.format_report(report, "financial")
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تحديث", callback_data='report_financial')],
                    [InlineKeyboardButton("🔙 التقارير", callback_data='reports_menu')]
                ]),
                parse_mode='Markdown'
            )
        
        elif data == 'report_users':
            report = ReportsHandler.generate_users_report()
            message = ReportsHandler.format_report(report, "users")
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تحديث", callback_data='report_users')],
                    [InlineKeyboardButton("🔙 التقارير", callback_data='reports_menu')]
                ]),
                parse_mode='Markdown'
            )
        
        elif data == 'reports_menu':
            await ReportsHandler.show_reports_menu(update, context)
        
        elif data == 'export_csv':
            await query.answer("📊 جاري تصدير البيانات...", show_alert=True)
            # كود تصدير CSV هنا
        
        elif data == 'live_stats':
            await query.edit_message_text(
                "📊 **الإحصائيات الفورية:**\n\n"
                "جارٍ تحديث البيانات...\n"
                "⏳ يرجى الانتظار",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 التقارير", callback_data='reports_menu')]
                ]),
                parse_mode='Markdown'
            )