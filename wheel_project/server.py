"""
JADO BOT — Luxury Roulette API + static hosting
All outcomes are determined server-side (secrets.SystemRandom).
"""
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from supabase import create_client

from roulette_service import RouletteService

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", ""))
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", os.environ.get("BOT_TOKEN", ""))

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
service = RouletteService(supabase, BOT_TOKEN) if supabase else None


def require_service():
    if not service:
        return jsonify({"success": False, "message": "Supabase not configured"}), 503
    return None


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/index.html")
def index_html():
    return send_from_directory(".", "index.html")


@app.route("/wheel.html")
def wheel_html():
    return send_from_directory(".", "index.html")


@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory("css", filename)


@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory("js", filename)


@app.route("/api/check-spin-eligibility", methods=["POST"])
@app.route("/api/check", methods=["POST"])
def api_check():
    err = require_service()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    tid, msg = service.resolve_user_id(body)
    if not tid:
        return jsonify({"allowed": False, "message": msg}), 400
    result = service.check_eligibility(tid)
    return jsonify(result)


@app.route("/api/spin-wheel", methods=["POST"])
@app.route("/api/spin", methods=["POST"])
def api_spin():
    err = require_service()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    tid, msg = service.resolve_user_id(body)
    if not tid:
        return jsonify({"success": False, "message": msg}), 400

    # Reject client-supplied results (anti-cheat)
    if body.get("result") or body.get("segment_index") is not None:
        return jsonify({"success": False, "message": "النتيجة تُحدد من السيرفر فقط"}), 400

    outcome = service.spin_wheel(tid)
    status = 200 if outcome.get("success") else 403
    return jsonify(outcome), status


@app.route("/api/claim-prize", methods=["POST"])
def api_claim():
    err = require_service()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    tid, msg = service.resolve_user_id(body)
    result_id = body.get("result_id")
    if not tid or not result_id:
        return jsonify({"success": False, "message": msg or "result_id مطلوب"}), 400
    return jsonify(service.claim_prize(tid, result_id))


@app.route("/api/save-result", methods=["POST"])
def api_save():
    err = require_service()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    tid, msg = service.resolve_user_id(body)
    result_id = body.get("result_id")
    if not tid or not result_id:
        return jsonify({"success": False, "message": msg or "result_id مطلوب"}), 400
    return jsonify(service.save_result(tid, result_id))


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "supabase": bool(supabase)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
