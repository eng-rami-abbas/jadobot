"""Server-side wheel segments — single source of truth."""

SEGMENT_COUNT = 8
SEGMENT_ARC = 360 / SEGMENT_COUNT

# Order clockwise from top (12 o'clock). Indices 2 & 6 are opposite "حظ أوفر".
SEGMENTS = [
    {"index": 0, "code": "cash_10000", "type": "cash", "amount": 10000, "label": "10,000", "label_ar": "10,000 ل.س", "color": "#8b1530", "color_end": "#5c0a1f"},
    {"index": 1, "code": "cash_20000", "type": "cash", "amount": 20000, "label": "20,000", "label_ar": "20,000 ل.س", "color": "#2d1f5e", "color_end": "#1a1240"},
    {"index": 2, "code": "none_a", "type": "none", "label": "حظ أوفر", "label_ar": "حظ أوفر", "color": "#8b1530", "color_end": "#5c0a1f"},
    {"index": 3, "code": "telegram_premium", "type": "premium", "label": "Premium", "label_ar": "تيليجرام بريميوم", "color": "#2d1f5e", "color_end": "#1a1240"},
    {"index": 4, "code": "cash_50000", "type": "cash", "amount": 50000, "label": "50,000", "label_ar": "50,000 ل.س", "color": "#8b1530", "color_end": "#5c0a1f"},
    {"index": 5, "code": "bonus_5", "type": "bonus", "percent": 5, "label": "5%", "label_ar": "بونص 5%", "color": "#2d1f5e", "color_end": "#1a1240"},
    {"index": 6, "code": "none_b", "type": "none", "label": "حظ أوفر", "label_ar": "حظ أوفر", "color": "#8b1530", "color_end": "#5c0a1f"},
    {"index": 7, "code": "respin", "type": "respin", "label": "Respin", "label_ar": "إعادة تدوير", "color": "#2d1f5e", "color_end": "#1a1240"},
]

# Relative weights (server-only random)
SEGMENT_WEIGHTS = [14, 10, 18, 4, 6, 12, 18, 8]


def segment_by_index(index: int) -> dict:
    return SEGMENTS[index % SEGMENT_COUNT]


def target_angle_for_segment(index: int, full_turns: int = 6) -> float:
    """Degrees wheel must rotate so segment center sits under top pointer."""
    center = index * SEGMENT_ARC + SEGMENT_ARC / 2
    return full_turns * 360 + (360 - center)
