from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
import os
from datetime import date, datetime

app = Flask(__name__)
CORS(app)

# ─── Supabase Config ───
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://your-project.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'your-anon-key')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_today():
    return str(date.today())

def get_user(user_id):
    try:
        response = supabase.table('users').select('*').eq('user_id', str(user_id)).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def create_user(user_id):
    try:
        data = {
            'user_id': str(user_id),
            'balance': 0,
            'pending_bonus': 0,
            'last_deposit_date': None,
            'last_deposit_amount': 0,
            'last_spin_date': None,
            'total_spins': 0,
            'total_wins': 0,
            'created_at': datetime.now().isoformat()
        }
        supabase.table('users').insert(data).execute()
        return data
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def update_user(user_id, updates):
    try:
        supabase.table('users').update(updates).eq('user_id', str(user_id)).execute()
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        return False

# ─── Static Files ───
@app.route('/')
def index():
    return send_from_directory('.', 'wheel.html')

@app.route('/wheel.html')
def serve_wheel():
    return send_from_directory('.', 'wheel.html')

@app.route('/back.jpg')
def serve_back():
    return send_from_directory('.', 'back.jpg')

@app.route('/pin.png')
def serve_pin():
    return send_from_directory('.', 'pin.png')

# ─── 1. Check Spin Eligibility ───
@app.route('/check', methods=['POST'])
def check_spin():
    data = request.json
    user_id = str(data.get('user_id'))
    if not user_id:
        return jsonify({'allowed': False, 'message': 'معرف المستخدم مفقود'}), 400

    user = get_user(user_id)
    today = get_today()

    if not user:
        user = create_user(user_id)
        if not user:
            return jsonify({'allowed': False, 'message': 'خطأ في إنشاء المستخدم'}), 500

    if user.get('last_deposit_date') != today:
        return jsonify({
            'allowed': False,
            'message': 'يجب أن تشحن اليوم للحصول على تدويرة مجانية'
        })

    if user.get('last_spin_date') == today:
        return jsonify({
            'allowed': False,
            'message': 'لقد استخدمت تدويرتك المجانية اليوم. عد غداً!'
        })

    return jsonify({'allowed': True})

# ─── 2. Perform Spin ───
@app.route('/spin', methods=['POST'])
def perform_spin():
    data = request.json
    user_id = str(data.get('user_id'))
    result = data.get('result')

    if not user_id or not result:
        return jsonify({'success': False, 'message': 'بيانات ناقصة'}), 400

    user = get_user(user_id)
    today = get_today()

    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    if user.get('last_deposit_date') != today:
        return jsonify({'success': False, 'message': 'لم تقم بالإيداع اليوم'}), 403
    if user.get('last_spin_date') == today:
        return jsonify({'success': False, 'message': 'لقد لعبت اليوم بالفعل'}), 403

    updates = {'last_spin_date': today}
    result_type = result.get('type')
    message = ""

    if result_type == 'cash':
        new_balance = user.get('balance', 0) + result['amount']
        updates['balance'] = new_balance
        updates['total_wins'] = user.get('total_wins', 0) + 1
        message = f"🎉 مبروك! تم إضافة {result['amount']:,} ل.س إلى رصيدك"
    elif result_type == 'bonus':
        new_bonus = user.get('pending_bonus', 0) + result['percent']
        updates['pending_bonus'] = new_bonus
        message = f"🔥 مبروك! حصلت على بونص {result['percent']}% يُضاف عند شحنك القادم"
    elif result_type == 'gift':
        message = f"🎁 مبروك! حصلت على: {result.get('label', 'هدية')}"
    elif result_type == 'none':
        message = "😔 حظ أوفر المرة القادمة"
    else:
        return jsonify({'success': False, 'message': 'نوع نتيجة غير معروف'}), 400

    updates['total_spins'] = user.get('total_spins', 0) + 1

    if update_user(user_id, updates):
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': 'خطأ في حفظ النتيجة'}), 500

# ─── 3. Record Deposit ───
@app.route('/deposit', methods=['POST'])
def record_deposit():
    data = request.json
    user_id = str(data.get('user_id'))
    amount = data.get('amount', 0)
    currency = data.get('currency', 'SYP')

    if not user_id:
        return jsonify({'success': False, 'message': 'معرف المستخدم مفقود'}), 400

    user = get_user(user_id)
    today = get_today()

    if not user:
        user = create_user(user_id)

    updates = {
        'last_deposit_date': today,
        'last_deposit_amount': amount,
        'last_deposit_currency': currency
    }

    pending_bonus = user.get('pending_bonus', 0)
    if pending_bonus > 0 and amount > 0:
        bonus_amount = int(amount * pending_bonus / 100)
        new_balance = user.get('balance', 0) + amount + bonus_amount
        updates['balance'] = new_balance
        updates['pending_bonus'] = 0
        message = f"تم الإيداع {amount:,} ل.س + بونص {bonus_amount:,} ل.س ({pending_bonus}%)"
    else:
        new_balance = user.get('balance', 0) + amount
        updates['balance'] = new_balance
        message = f"تم الإيداع {amount:,} ل.س بنجاح"

    if update_user(user_id, updates):
        return jsonify({
            'success': True,
            'message': message,
            'balance': new_balance,
            'pending_bonus': updates.get('pending_bonus', 0)
        })
    else:
        return jsonify({'success': False, 'message': 'خطأ في تحديث البيانات'}), 500

# ─── 4. Get User Data ───
@app.route('/user/<user_id>', methods=['GET'])
def get_user_data(user_id):
    user = get_user(user_id)
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

# ─── 5. Get Stats ───
@app.route('/stats/<user_id>', methods=['GET'])
def get_stats(user_id):
    user = get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'balance': user.get('balance', 0),
        'pending_bonus': user.get('pending_bonus', 0),
        'total_spins': user.get('total_spins', 0),
        'total_wins': user.get('total_wins', 0),
        'last_deposit_date': user.get('last_deposit_date'),
        'last_spin_date': user.get('last_spin_date'),
        'can_spin_today': user.get('last_deposit_date') == get_today() and user.get('last_spin_date') != get_today()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
