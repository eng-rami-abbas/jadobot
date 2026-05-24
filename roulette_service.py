"""Business logic for JADO Roulette — Supabase + Damascus day rules."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date, datetime
from typing import Any, Optional
from urllib.parse import parse_qsl

import pytz
from supabase import Client

from roulette_config import SEGMENTS, SEGMENT_WEIGHTS, segment_by_index, target_angle_for_segment

DAMASCUS = pytz.timezone("Asia/Damascus")
AMOUNT_SCALE = 100  # balance_syp uses same scale as bot deposits


def damascus_today() -> date:
    return datetime.now(DAMASCUS).date()


def validate_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    if not init_data or not bot_token:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if calculated != received_hash:
            return None
        user_raw = parsed.get("user")
        if user_raw:
            import json
            return json.loads(user_raw)
        return {"id": parsed.get("user_id")}
    except Exception:
        return None


def _telegram_ids(telegram_id: int | str) -> list:
    tid = int(telegram_id)
    return [tid, str(tid)]


class RouletteService:
    def __init__(self, client: Client, bot_token: str = ""):
        self.db = client
        self.bot_token = bot_token
        self._rng = secrets.SystemRandom()

    def resolve_user_id(self, body: dict) -> tuple[Optional[int], Optional[str]]:
        init_data = body.get("init_data") or body.get("initData")
        if init_data and self.bot_token:
            user = validate_telegram_init_data(init_data, self.bot_token)
            if user and user.get("id"):
                return int(user["id"]), None
            return None, "بيانات Telegram غير صالحة"
        raw = body.get("telegram_id") or body.get("user_id")
        if raw:
            return int(raw), None
        return None, "معرف المستخدم مفقود"

    def has_deposit_today(self, telegram_id: int) -> bool:
        today_start = datetime.now(DAMASCUS).replace(hour=0, minute=0, second=0, microsecond=0)
        for tid in _telegram_ids(telegram_id):
            res = (
                self.db.table("transactions")
                .select("id")
                .eq("type", "deposit")
                .eq("status", "completed")
                .eq("telegram_id", tid)
                .gte("created_at", today_start.isoformat())
                .limit(1)
                .execute()
            )
            if res.data:
                return True
        return False

    def get_wheel_row(self, telegram_id: int) -> dict:
        for tid in _telegram_ids(telegram_id):
            res = (
                self.db.table("wheel_spins")
                .select("*")
                .eq("telegram_id", str(tid))
                .maybe_single()
                .execute()
            )
            if res.data:
                return res.data
        return {"telegram_id": str(telegram_id), "extra_spins": 0, "pending_bonus_percent": 0}

    def spun_today(self, telegram_id: int) -> bool:
        row = self.get_wheel_row(telegram_id)
        last = row.get("last_spin_at")
        if not last:
            return False
        try:
            ts = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = DAMASCUS.localize(ts)
            return ts.astimezone(DAMASCUS).date() == damascus_today()
        except Exception:
            return False

    def count_spins_today(self, telegram_id: int) -> int:
        today = str(damascus_today())
        res = (
            self.db.table("spins")
            .select("id", count="exact")
            .eq("telegram_id", int(telegram_id))
            .eq("spin_date", today)
            .execute()
        )
        return res.count or 0

    def check_eligibility(self, telegram_id: int) -> dict:
        if not self.has_deposit_today(telegram_id):
            return {
                "allowed": False,
                "code": "no_deposit",
                "message": "🔒 يجب إتمام إيداع اليوم للحصول على لفة مجانية.",
            }

        wheel = self.get_wheel_row(telegram_id)
        extra = int(wheel.get("extra_spins") or 0)

        if self.spun_today(telegram_id) and extra <= 0:
            return {
                "allowed": False,
                "code": "daily_limit",
                "message": "⏰ استخدمت لفة اليوم. عد غداً بعد إيداع جديد.",
            }

        return {
            "allowed": True,
            "message": "يمكنك التدوير الآن",
            "extra_spins": extra,
            "segments": [
                {"index": s["index"], "label_ar": s["label_ar"], "type": s["type"]}
                for s in SEGMENTS
            ],
        }

    def pick_segment(self) -> int:
        return self._rng.choices(
            list(range(len(SEGMENTS))), weights=SEGMENT_WEIGHTS, k=1
        )[0]

    def spin_wheel(self, telegram_id: int) -> dict:
        elig = self.check_eligibility(telegram_id)
        if not elig.get("allowed"):
            return {"success": False, **elig}

        wheel = self.get_wheel_row(telegram_id)
        extra = int(wheel.get("extra_spins") or 0)
        is_bonus_spin = self.spun_today(telegram_id) and extra > 0

        segment_index = self.pick_segment()
        segment = segment_by_index(segment_index)
        angle = target_angle_for_segment(segment_index)
        today = str(damascus_today())

        spin_row = (
            self.db.table("spins")
            .insert({
                "telegram_id": int(telegram_id),
                "spin_date": today,
                "is_bonus_spin": is_bonus_spin,
            })
            .execute()
        )
        spin_id = spin_row.data[0]["id"] if spin_row.data else None

        result_row = (
            self.db.table("spin_results")
            .insert({
                "spin_id": spin_id,
                "telegram_id": int(telegram_id),
                "segment_index": segment_index,
                "prize_type": segment["type"],
                "prize_code": segment["code"],
                "prize_payload": {
                    "amount": segment.get("amount"),
                    "percent": segment.get("percent"),
                    "label_ar": segment["label_ar"],
                },
                "target_angle": angle,
                "claimed": False,
            })
            .execute()
        )
        result_id = result_row.data[0]["id"] if result_row.data else None

        now_iso = datetime.now(DAMASCUS).isoformat()
        upsert = {
            "telegram_id": str(telegram_id),
            "last_spin_at": now_iso,
            "updated_at": now_iso,
        }
        if is_bonus_spin and extra > 0:
            upsert["extra_spins"] = max(0, extra - 1)
        self.db.table("wheel_spins").upsert(upsert, on_conflict="telegram_id").execute()

        return {
            "success": True,
            "spin_id": spin_id,
            "result_id": result_id,
            "segment_index": segment_index,
            "target_angle": angle,
            "prize": {
                "type": segment["type"],
                "code": segment["code"],
                "label_ar": segment["label_ar"],
                "amount": segment.get("amount"),
                "percent": segment.get("percent"),
            },
            "segment": segment,
            "is_bonus_spin": is_bonus_spin,
        }

    def claim_prize(self, telegram_id: int, result_id: str) -> dict:
        res = (
            self.db.table("spin_results")
            .select("*")
            .eq("id", result_id)
            .eq("telegram_id", int(telegram_id))
            .maybe_single()
            .execute()
        )
        if not res.data:
            return {"success": False, "message": "النتيجة غير موجودة"}

        row = res.data
        if row.get("claimed"):
            return {"success": True, "message": "تم صرف الجائزة مسبقاً", "already_claimed": True}

        payload = row.get("prize_payload") or {}
        prize_type = row.get("prize_type")
        message = ""

        if prize_type == "cash":
            amount = int(payload.get("amount") or 0)
            credit = amount * AMOUNT_SCALE
            balance = self._add_balance(telegram_id, credit)
            message = f"🎉 مبروك! ربحت {amount:,} ل.س\n💳 رصيدك: {balance / AMOUNT_SCALE:,.0f} ل.س"

        elif prize_type == "bonus":
            percent = float(payload.get("percent") or 5)
            self.db.table("wheel_spins").upsert({
                "telegram_id": str(telegram_id),
                "pending_bonus_percent": percent,
                "updated_at": datetime.now(DAMASCUS).isoformat(),
            }, on_conflict="telegram_id").execute()
            self.db.table("bonus_rewards").insert({
                "telegram_id": int(telegram_id),
                "percent": percent,
                "spin_result_id": result_id,
            }).execute()
            message = f"🎉 مبروك! بونص {percent:g}% على أول إيداع قادم (مرة واحدة)."

        elif prize_type == "premium":
            self.db.table("telegram_premium_rewards").insert({
                "telegram_id": int(telegram_id),
                "status": "pending",
                "spin_result_id": result_id,
                "notes": "Telegram Premium — wheel prize",
            }).execute()
            message = "🎁 مبروك! فزت بـ Telegram Premium.\nسيتواصل معك الدعم قريباً."

        elif prize_type == "respin":
            wheel = self.get_wheel_row(telegram_id)
            extra = int(wheel.get("extra_spins") or 0) + 1
            self.db.table("wheel_spins").upsert({
                "telegram_id": str(telegram_id),
                "extra_spins": extra,
                "updated_at": datetime.now(DAMASCUS).isoformat(),
            }, on_conflict="telegram_id").execute()
            message = "🔄 مبروك! حصلت على إعادة تدوير مجانية.\nاضغط SPIN مرة أخرى الآن!"

        else:
            message = "😔 حظ أوفر!\nحاول مرة أخرى غداً بعد إيداع."

        self.db.table("spin_results").update({"claimed": True}).eq("id", result_id).execute()

        return {
            "success": True,
            "message": message,
            "prize_type": prize_type,
            "telegram_message": message,
        }

    def _add_balance(self, telegram_id: int, credit: int) -> float:
        for tid in _telegram_ids(telegram_id):
            res = self.db.table("users").select("id,balance_syp").eq("telegram_id", tid).execute()
            if res.data:
                user = res.data[0]
                new_bal = float(user.get("balance_syp") or 0) + credit
                self.db.table("users").update({"balance_syp": new_bal}).eq("id", user["id"]).execute()
                return new_bal
        return float(credit)

    def save_result(self, telegram_id: int, result_id: str) -> dict:
        """Alias used by API — claim applies the prize."""
        return self.claim_prize(telegram_id, result_id)
