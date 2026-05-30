# إصلاحات ملفات ConversationHandler - إضافة per_message=True
# ============================================================
# لكل ملف، ابحث عن ConversationHandler وأضف per_message=True
# ============================================================

# ============================================================
# 1. handlers/reseiveGifts.py
# ============================================================
# الأصلي:
"""
def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_reseive_gift_handler, pattern='^reseive_gift$')],
        states={
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    return conv_handler
"""
# المُصلَح:
"""
def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_reseive_gift_handler, pattern='^reseive_gift$')],
        states={
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True,
        per_user=True,
        allow_reentry=True,
    )
    return conv_handler
"""

# ============================================================
# 2. handlers/gift_code.py
# ============================================================
# الأصلي:
"""
    return ConversationHandler(
        ...
        allow_reentry=True,
        per_user=True
    )
"""
# المُصلَح:
"""
    return ConversationHandler(
        ...
        allow_reentry=True,
        per_user=True,
        per_message=True,
    )
"""

# ============================================================
# 3. handlers/depositAccount.py
# ============================================================
# الأصلي:
"""
def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_deposit_account_handler, pattern="^deposit_account$")],
        states={
            AMMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ammount_for_deposit)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    return conv_handler
"""
# المُصلَح:
"""
def conversationHandler():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_deposit_account_handler, pattern="^deposit_account$")],
        states={
            AMMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ammount_for_deposit)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True,
        per_user=True,
        allow_reentry=True,
    )
    return conv_handler
"""

# ============================================================
# 4. handlers/withdrawalAccount.py
# ============================================================
# نفس التغيير كما depositAccount.py
"""
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=True,
    per_user=True,
    allow_reentry=True,
"""

# ============================================================
# 5. handlers/adminMessage.py
# ============================================================
# نفس التغيير كما depositAccount.py
"""
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=True,
    per_user=True,
    allow_reentry=True,
"""

# ============================================================
# 6. handlers/deposit.py
# ============================================================
# الأصلي:
"""
    return ConversationHandler(
        ...
        allow_reentry=True,
        per_user=True
    )
"""
# المُصلَح:
"""
    return ConversationHandler(
        ...
        allow_reentry=True,
        per_user=True,
        per_message=True,
    )
"""

# ============================================================
# 7. handlers/withdrawal_conversation.py
# ============================================================
# نفس التغيير كما deposit.py
"""
    allow_reentry=True,
    per_user=True,
    per_message=True,
"""

# ============================================================
# 8. handlers/sendGifts.py
# ============================================================
# نفس التغيير كما deposit.py
"""
    per_user=True,
    allow_reentry=True,
    per_message=True,
"""

# ============================================================
# 9. handlers/support_system.py
# ============================================================
# الأصلي:
"""
    @staticmethod
    def get_conversation_handler():
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(SupportSystem.send_to_admin, pattern='^send_to_admin$')],
            states={
                SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, SupportSystem.handle_support_message)]
            },
            fallbacks=[CommandHandler('cancel', SupportSystem.cancel_support)],
        )
"""
# المُصلَح:
"""
    @staticmethod
    def get_conversation_handler():
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(SupportSystem.send_to_admin, pattern='^send_to_admin$')],
            states={
                SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, SupportSystem.handle_support_message)]
            },
            fallbacks=[CommandHandler('cancel', SupportSystem.cancel_support)],
            per_message=True,
            per_user=True,
            allow_reentry=True,
        )
"""

# ============================================================
# 10. handlers/createAccount.py (إضافي)
# ============================================================
# الأصلي:
"""
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_create_account_handler, pattern='^ichancy_create_account$')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
"""
# المُصلَح:
"""
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_create_account_handler, pattern='^ichancy_create_account$')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True,
        per_user=True,
        allow_reentry=True,
    )
"""
