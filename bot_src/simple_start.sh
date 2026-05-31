#!/bin/bash
import os

echo "========================================"
echo "iChancy Bot - Simple Start"
echo "========================================"

# تفعيل venv
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --quiet
fi

# إنشاء ملفات config إذا لزم
mkdir -p config

if [ ! -f "config/telegram.py" ]; then
    cat > config/telegram.py << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_TELEGRAM_ID = "7179419936"
ADMIN_CHAT_ID = None
COOKIE_STRING = "languageCode=ar_IQ; PHPSESSID_3a07edcde6f57a008f3251235df79776a424dd7623e40d4250e37e4f1f15fadf=f938e56fdee08c821e7a9907784d3a1e; __cf_bm=yOChR_HG6nLR8GFTsKqPUqg7oVDoy0UiVBQN06169Z8-1767122047-1.0.1.1-m9H1HyQzEJzepg9Je_loQC5CvBdVBCLDX2XFam2OastPyaWgP.g9qoIWmJ5jZC1b4b43W0QixrcMsKnDuomHO5Xm5HbzN2ORRgjggLr2ybc; cf_clearance=l6g5Ddn_eHtO0DY2IY3GgGRr0M7woP63JzqDUJoDRx0-1767122096-1.2.1.1-xl0YVXR_4YRLDjiKHuv29zMdyjS0CWXMOnjQAzn0yxH82VKf_3jPP1YAEcwOmYeGRY9wyk6Ob4FqpdEzysSdEEMzbeMOcZJjI_MrK8WnUsuwKpyTFGlmgEARe4_lRkkOIareLPM2FYI8FUrPuQwNFAZtIxIwQsnKsIDMuiLvNPCK2RfrfrQaJGcCkF_I1b0QgrQVk_DeEsC0tLGFP1trynS58TZUvQgNkobdQR8fx4Y"
def validate_tokens():
    if not TOKEN:
        raise ValueError("Telegram bot token is not set")
    if not COOKIE_STRING:
        raise ValueError("Cookie string is not set")
    return True
EOF
fi

echo ""
echo "========================================"
echo "CHOOSE OPTION:"
echo "1. Start Bot Only"
echo "2. Start Cookie Service + Bot"
echo "3. Manual Mode (Two Terminals)"
echo "========================================"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "Starting Bot..."
        python bot.py
        ;;
    2)
        echo "Starting Cookie Service in background..."
        nohup python cookie_service.py > cookie.log 2>&1 &
        COOKIE_PID=$!
        echo "Cookie PID: $COOKIE_PID"
        sleep 10
        echo "Starting Bot..."
        python bot.py
        kill $COOKIE_PID 2>/dev/null
        ;;
    3)
        echo ""
        echo "OPEN TWO TERMINAL WINDOWS:"
        echo ""
        echo "TERMINAL 1 - Cookie Service:"
        echo "source venv/bin/activate"
        echo "python cookie_service.py"
        echo ""
        echo "TERMINAL 2 - Bot:"
        echo "source venv/bin/activate"
        echo "python bot.py"
        echo ""
        echo "Press Enter to continue..."
        read
        ;;
    *)
        echo "Invalid choice"
        ;;
esac

echo "========================================"
echo "Done"
echo "========================================"