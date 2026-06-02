"""
Health check endpoint for Railway
"""
import os
from flask import Flask, jsonify
from database.supabase_client import supabase_client

app = Flask(__name__)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test Supabase connection
        client = supabase_client.get_client()
        result = client.table('users').select('count').limit(1).execute()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development')
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'database': 'disconnected'
        }), 503

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram bot"""
    # This will be handled by python-telegram-bot
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
