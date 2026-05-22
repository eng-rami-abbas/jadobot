# Debugging Guide for iChancy Account Creation

## Common Errors and Solutions

### 1. "Sign-in failed: 403 Forbidden"

**Root Cause**: Invalid iChancy credentials

**Solution**:
1. Double-check `ICHANCY_USERNAME` in `.env`
2. Double-check `ICHANCY_PASSWORD` in `.env`
3. Verify credentials work directly on agents.ichancy.com
4. Check if account is active and has proper permissions

**Debug**:
```python
# Add this to test credentials
api = iChancyAPI()
api._sign_in()  # Check logs for detailed error
```

**Log Output**:
```
ERROR - Sign-in failed: 403 Forbidden
ERROR - Username: [your_email]
ERROR - URL: https://agents.ichancy.com/global/api/UserApi/signin
```

---

### 2. "ParentId property is required"

**Root Cause**: PARENT_ID is missing or not being sent

**Solution**:
1. Ensure `PARENT_ID` is set in `.env`
2. If not set, default `2730826` should be used
3. Verify PARENT_ID is a valid agent ID

**Debug**:
```python
# Check in logs:
logger.info(f"Using parent_id: {parent_id}")

# This should print the PARENT_ID being used
```

**Log Output**:
```
INFO - Using parent_id: 2730826
INFO - Registration payload: {..., 'parentId': '2730826'}
```

---

### 3. "Duplicate login"

**Root Cause**: Username already exists in the system

**Solution**:
1. User should choose a different username
2. Check if username already exists via ichancy.com
3. Consider adding random suffix to username

**User Message**:
```
❌ اسم المستخدم مستخدم بالفعل! الرجاء اختيار اسم آخر.
```

**Prevention**:
- Add username availability check before registration
- Suggest adding timestamp or random suffix

---

### 4. "Duplicate email"

**Root Cause**: Email already registered

**Solution**:
1. Email generation uses randomized suffix (should be unique)
2. If this occurs frequently, use better email generation
3. Consider accepting user-provided email

**Current Method**:
```python
email = f"{base_name_clean}_{random_suffix}@players.ichancy.com"
# Should be unique with 6-char random suffix
```

**If Problem Persists**:
```python
# Use timestamp-based email
import time
email = f"{base_name_clean}_{int(time.time())}@players.ichancy.com"
```

---

### 5. "Player not found" after successful registration

**Root Cause**: Player exists but lookup is failing

**Possible Issues**:
- API server delay in propagating data
- Filter not matching correctly
- Database synchronization issue

**Solution**:
The code already retries 5 times with 1-second delays. If still failing:

```python
# Increase retry count or delay
for i in range(10):  # Increase from 5
    try:
        verify = api.get_player_id_by_username(name)
        logger.info(f"Verification attempt {i+1}: {verify}")
    except Exception as e:
        logger.error(f"VERIFY ERROR (attempt {i+1}): {e}")
    
    if verify:
        break
    
    await asyncio.sleep(2)  # Increase from 1 second
```

---

### 6. HTTP 422 with no error message

**Root Cause**: API validation error without clear message

**Debug Steps**:
1. Check the full response in logs
2. Look for specific field errors

**Fix**:
```python
if response.status_code == 422:
    try:
        data = response.json()
        logger.error(f"422 Full response: {data}")
        notifications = data.get('notification', [])
        for notif in notifications:  # Check all notifications
            logger.error(f"Error: {notif.get('content')}")
    except:
        logger.error(f"422 Raw: {response.text}")
```

---

### 7. "Invalid JSON response"

**Root Cause**: API returned non-JSON response (usually Cloudflare error)

**Solution**:
1. Ensure cloudscraper is installed: `pip install cloudscraper`
2. Check internet connection
3. Verify API endpoint is accessible

**Debug**:
```python
try:
    data = response.json()
except Exception as e:
    logger.error(f"Failed to parse response: {e}")
    logger.error(f"Status: {response.status_code}")
    logger.error(f"Headers: {response.headers}")
    logger.error(f"Content-Type: {response.headers.get('content-type')}")
    logger.error(f"First 500 chars: {response.text[:500]}")
```

---

## Monitoring Checklist

### In Logs (Daily)

```bash
# Check for successful registrations
grep "successful" bot.log

# Check for errors
grep "ERROR" bot.log | tail -20

# Check authentication
grep "sign in" bot.log

# Check specific registrations
grep "Registering player:" bot.log
```

### Success Indicators

```
✅ "Successfully signed in to iChancy API"
✅ "Registering player: [username]"
✅ "Register response status: 200"
✅ "Registration successful! Player ID response:"
✅ "Verification attempt 1: [player_id]"
✅ "Account not confirmed, but continuing anyway"
✅ "Successfully saved to database"
```

### Error Indicators

```
❌ "Sign-in failed: 403"
❌ "422 Validation error"
❌ "No access token"
❌ "Player not found"
❌ "Invalid JSON response"
❌ "Authentication failed"
```

---

## Database Verification

After account creation, verify database entry:

```python
# In bot_src:
import store

telegram_id = "123456789"
user = store.getUserByTelegramId(telegram_id)

print(f"ichancy_account: {user.get('ichancy_account')}")
print(f"ichancy_player_id: {user.get('ichancy_player_id')}")
print(f"ichancy_email: {user.get('ichancy_email')}")
```

Expected output:
```
ichancy_account: testuser123
ichancy_player_id: 12345
ichancy_email: testuser_abc123@players.ichancy.com
```

---

## API Response Validation

### Successful Response:
```json
{
  "status": true,
  "html": "",
  "result": 1,
  "notification": []
}
```

### Error Response:
```json
{
  "status": false,
  "html": "",
  "result": null,
  "notification": [
    {
      "code": 1,
      "content": "Error message here",
      "title": "",
      "autoHideAfter": 5000,
      "list": [],
      "status": "error"
    }
  ]
}
```

## Performance Monitoring

### Add timing logs:

```python
import time

start_time = time.time()

result = api.register_player(...)

elapsed = time.time() - start_time
logger.info(f"Registration took {elapsed:.2f} seconds")

# Log warning if slow
if elapsed > 10:
    logger.warning(f"Registration slow: {elapsed:.2f}s")
```

### Expected Timing:
- Sign-in: < 3 seconds
- Registration: < 2 seconds
- Player lookup: < 1 second
- Total: < 10 seconds

If taking longer:
- Check network connection
- Check API performance
- Consider increasing timeouts

---

## Testing Toolkit

### Unit Test Template:

```python
import unittest
from services.iChancyAPI import iChancyAPI

class TestiChancyAPI(unittest.TestCase):
    
    def setUp(self):
        self.api = iChancyAPI()
    
    def test_authentication(self):
        """Test sign-in functionality"""
        result = self.api._ensure_authenticated()
        self.assertTrue(result, "Authentication should succeed")
    
    def test_register_player(self):
        """Test player registration"""
        result = self.api.register_player(
            username="testuser_" + str(int(time.time())),
            password="Test@1234",
            email="test_" + str(int(time.time())) + "@players.ichancy.com",
            parent_id="2730826"
        )
        self.assertTrue(result['success'], f"Registration should succeed: {result}")
```

### Run Tests:
```bash
python -m pytest services/iChancyAPI.py -v
```

---

## Emergency Procedures

### If API is Down:

```python
# Add fallback notification to admin
if not api._ensure_authenticated():
    # Send alert to admin
    await bot.send_message(
        chat_id=ADMIN_ID,
        text="⚠️ iChancy API is unreachable!"
    )
    # Inform user
    await update.message.reply_text(
        "❌ الخدمة غير متاحة حالياً. جرب لاحقاً."
    )
```

### If Database is Down:

```python
try:
    store.insertUserDetailes(...)
except Exception as e:
    logger.error(f"Database error: {e}")
    # Still inform user of successful registration
    await update.message.reply_text(
        "✅ تم إنشاء الحساب بنجاح لكن حفظ البيانات فشل. تواصل مع الدعم."
    )
```

---

## Contact & Support

For issues not covered here:

1. **Check Logs**: `/bot_src/data/bot.log`
2. **Enable Debug Mode**: Set `DEBUG=true` in `.env`
3. **Increase Logging**: Add more logger statements
4. **Contact Admin**: Report with full error details and timestamp

---

## Quick Reference

| Error | Cause | Fix |
|-------|-------|-----|
| 403 | Bad credentials | Check .env |
| 422 | Validation error | Check email/username |
| 401 | Token expired | Refresh token |
| Duplicate login | Username exists | Choose different |
| Duplicate email | Email exists | Shouldn't happen with auto-gen |
| Player not found | Lookup delay | Wait and retry |
| Invalid JSON | Cloudflare | Check proxy |
| Database error | Connection issue | Check supabase |

