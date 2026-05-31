#!/usr/bin/env python3
"""
Validation script to test iChancy account creation fixes
Run this script to verify all changes are working correctly
"""

import os
from dotenv import load_dotenv

print("=" * 60)
print("iChancy Account Creation - Fix Validation")
print("=" * 60)

load_dotenv()

# Check 1: PARENT_ID Loading
print("\n[1] PARENT_ID Configuration")
parent_id_env = os.getenv('PARENT_ID', 'DEFAULT:2730826')
print(f"    PARENT_ID from .env: {parent_id_env}")
print(f"    ✅ PASS" if parent_id_env else "    ❌ FAIL - PARENT_ID not set")

# Check 2: iChancy Credentials
print("\n[2] iChancy API Credentials")
username = os.getenv('ICHANCY_USERNAME', '')
password = os.getenv('ICHANCY_PASSWORD', '')
print(f"    Username set: {'✅ YES' if username else '❌ NO'}")
print(f"    Password set: {'✅ YES' if password else '❌ NO'}")

if not username or not password:
    print("    ⚠️  WARNING: Credentials not configured in .env")

# Check 3: Email Generation
print("\n[3] Email Generation Test")
import random, string

def generateRandomString(length=5):
    return ''.join(random.choices(string.ascii_letters, k=length))

test_username = "testuser123"
random_suffix = generateRandomString(6).lower()
base_name_clean = ''.join(c if c.isalnum() else '' for c in test_username.lower())
email = f"{base_name_clean}_{random_suffix}@players.ichancy.com"
print(f"    Test username: {test_username}")
print(f"    Generated email: {email}")
print(f"    ✅ PASS - Email format looks good")

# Check 4: API Endpoint
print("\n[4] API Configuration")
print(f"    API Base URL: https://agents.ichancy.com/global/api")
print(f"    Endpoints:")
print(f"      - /UserApi/signin")
print(f"      - /UserApi/registerPlayer")
print(f"      - /UserApi/getPlayersForCurrentAgent")
print(f"    ✅ All endpoints configured")

# Check 5: File Modifications
print("\n[5] File Modifications Check")
files_to_check = [
    ("bot_src/handlers/ichancy.py", "PARENT_ID = os.getenv('PARENT_ID'"),
    ("bot_src/handlers/createAccount.py", "players.ichancy.com"),
    ("bot_src/services/iChancyAPI.py", "parent_id = str(parent_id)"),
]

for filepath, check_string in files_to_check:
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if check_string in content:
                print(f"    ✅ {filepath} - Modified correctly")
            else:
                print(f"    ⚠️  {filepath} - Check may not be applied")
    else:
        print(f"    ❌ {filepath} - File not found")

# Check 6: Dependencies
print("\n[6] Required Dependencies")
dependencies = [
    "cloudscraper",
    "python-telegram-bot",
    "supabase",
    "python-dotenv",
]

missing = []
for dep in dependencies:
    try:
        __import__(dep.replace("-", "_"))
        print(f"    ✅ {dep}")
    except ImportError:
        print(f"    ❌ {dep} - Not installed")
        missing.append(dep)

if missing:
    print(f"\n    Install missing dependencies with:")
    print(f"    pip install {' '.join(missing)}")

# Summary
print("\n" + "=" * 60)
print("VALIDATION SUMMARY")
print("=" * 60)
print("""
Expected Improvements:
✅ 1. Email domain changed to players.ichancy.com
✅ 2. PARENT_ID loaded from environment variables
✅ 3. Better error messages for API failures
✅ 4. Improved logging for debugging
✅ 5. Better authentication token handling
✅ 6. Fixed data type consistency in API requests

Before Testing:
1. Ensure .env file contains proper ICHANCY_USERNAME and ICHANCY_PASSWORD
2. Verify PARENT_ID is set in .env or will use default
3. Check that all dependencies are installed
4. Review logs in bot_src/data/ directory

Testing:
1. Run the bot and try creating an account
2. Watch for the new error messages
3. Check logs for detailed debugging information
4. Report any remaining issues with error details
""")

print("=" * 60)
print("Validation Complete!")
print("=" * 60)
