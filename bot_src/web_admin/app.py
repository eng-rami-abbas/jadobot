from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

# =========================
# ترجمة
# =========================
def get_translation(key):
    translations = {
        "active_users_week": "Active Users (Week)",
        "total_balance": "Total Balance",
        "deposits_week": "Deposits (Week)",
        "withdrawals_week": "Withdrawals (Week)",
        "exchange_rate": "Exchange Rate"
    }
    return translations.get(key, key)

app.jinja_env.globals.update(get_translation=get_translation)

# =========================
# فلتر أرقام
# =========================
@app.template_filter('number_format')
def number_format(value):
    try:
        return "{:,}".format(int(value))
    except:
        return "0"

# =========================
# بيانات النظام (مرتبطة بالبوت)
# =========================
stats = {
    "active_users": 0,
    "total_balance": 0,
    "deposits_week": 0,
    "withdrawals_week": 0,
    "total_events": 0,
}

exchange_rate = 15000

bot_status = {
    "online": True,
    "last_check": datetime.now()
}

users = []
messages = []
deposit_logs = []
withdrawal_logs = []

# =========================
# GLOBAL CONTEXT (مهم جداً)
# =========================
@app.context_processor
def inject_globals():
    return dict(
        stats=stats,
        exchange_rate=exchange_rate,
        bot_status=bot_status,
        user={"name": "Admin"},
        sidebar={"visible": True}
    )

# =========================
# الصفحات
# =========================
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/users')
def users_page():
    return render_template('users.html', users=users)

@app.route('/messages')
def messages_page():
    return render_template('messages.html', messages=messages)

@app.route('/deposit_logs')
def deposit_logs_page():
    return render_template('deposit_logs.html', logs=deposit_logs)

@app.route('/withdrawal_logs')
def withdrawal_logs_page():
    return render_template('withdrawal_logs.html', logs=withdrawal_logs)

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

@app.route('/login')
def login():
    return render_template('login.html')

# =========================
# API من البوت
# =========================
@app.route('/api/events', methods=['POST'])
def receive_event():
    global stats

    data = request.json
    print("Event received:", data)

    if not data:
        return jsonify({"status": "no data"})

    stats["active_users"] = int(data.get("active_users", stats["active_users"]))
    stats["total_balance"] = int(data.get("total_balance", stats["total_balance"]))
    stats["deposits_week"] = int(data.get("deposits_week", stats["deposits_week"]))
    stats["withdrawals_week"] = int(data.get("withdrawals_week", stats["withdrawals_week"]))
    stats["total_events"] += 1

    # تحديث الحالة
    bot_status["last_check"] = datetime.now()

    # تخزين بيانات
    if data.get("type") == "deposit":
        deposit_logs.append(data)
    elif data.get("type") == "withdraw":
        withdrawal_logs.append(data)
    elif data.get("type") == "message":
        messages.append(data)
    elif data.get("type") == "user":
        users.append(data)

    return jsonify({"status": "ok"})

# =========================
# تحديث سعر الصرف
# =========================
@app.route('/api/exchange_rate/update', methods=['POST'])
def update_exchange_rate():
    global exchange_rate
    data = request.json

    try:
        exchange_rate = int(data.get("exchange_rate", exchange_rate))
        return jsonify({"success": True})
    except:
        return jsonify({"success": False, "message": "Invalid rate"})

# =========================
# تشغيل
# =========================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)