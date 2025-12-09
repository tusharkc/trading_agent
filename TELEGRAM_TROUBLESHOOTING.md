# Telegram Bot Troubleshooting Guide

## Issue: Bot Not Responding to Commands

If your Telegram bot isn't responding to `/help` or other commands, follow these steps:

### Step 1: Check Railway Logs

1. Go to Railway dashboard → Your service → **Logs** tab
2. Look for these messages:
   - ✅ `🤖 Telegram bot started and ready to receive commands` - Bot is running
   - ❌ `ERROR: TELEGRAM_BOT_TOKEN not set` - Token missing
   - ❌ `ERROR: TELEGRAM_CHAT_ID not set` - Chat ID missing
   - ❌ `Error running Telegram bot:` - Bot crashed

### Step 2: Verify Environment Variables

In Railway dashboard → **Variables** tab, check:

1. **TELEGRAM_BOT_TOKEN**:
   - Should start with numbers (e.g., `1234567890:ABC...`)
   - No spaces or extra characters
   - Get from @BotFather

2. **TELEGRAM_CHAT_ID**:
   - Should be a number (e.g., `123456789`)
   - No quotes or spaces
   - Get from @userinfobot

### Step 3: Test Bot Token

1. Open Telegram → Search for your bot (the username you created)
2. Click **Start** - You should see a welcome message
3. If you don't see the bot, the token might be wrong

### Step 4: Verify Bot is Running

Check Railway logs for:
```
✅ Telegram bot is running and ready!
🤖 Telegram bot started and ready to receive commands
```

If you don't see these, the bot might not have started.

### Step 5: Common Issues

#### Issue: "Unauthorized access"
- **Cause**: Your Chat ID doesn't match
- **Fix**: Get your Chat ID from @userinfobot and update `TELEGRAM_CHAT_ID`

#### Issue: Bot not found in Telegram
- **Cause**: Wrong bot token or bot not created
- **Fix**: Create new bot with @BotFather and update token

#### Issue: Bot starts but doesn't respond
- **Cause**: Bot might be crashing on command handling
- **Fix**: Check Railway logs for error messages

#### Issue: No logs at all
- **Cause**: Bot might not be starting
- **Fix**: Check if `bot_orchestrator.py` is the start command

### Step 6: Test Commands

Try these commands in order:

1. `/help` - Should work without authorization
2. `/start` - Requires authorization (your Chat ID)
3. `/status` - Requires authorization

If `/help` doesn't work, the bot isn't receiving updates.

### Step 7: Check Bot Status

In Railway:
1. Go to **Metrics** tab
2. Check if service is **Running** (green dot)
3. Check CPU/Memory usage

### Step 8: Manual Test

If bot still doesn't work, test locally:

1. Set environment variables in `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

2. Run locally:
   ```bash
   python bot_orchestrator.py
   ```

3. Send `/help` to your bot
4. Check console output for errors

### Step 9: Railway-Specific Issues

#### Bot stops after deployment
- Railway might be restarting
- Check **Deployments** tab for recent deployments
- Wait for deployment to complete

#### Environment variables not loading
- Make sure variables are set in Railway dashboard
- Redeploy after adding variables
- Check variable names match exactly (case-sensitive)

### Step 10: Get Help

If still not working:

1. **Check Railway logs** - Look for error messages
2. **Check bot token** - Verify with @BotFather
3. **Check chat ID** - Verify with @userinfobot
4. **Test locally** - Run `python bot_orchestrator.py` locally
5. **Check start command** - Should be `python bot_orchestrator.py`

## Quick Checklist

- [ ] Bot token is set in Railway variables
- [ ] Chat ID is set in Railway variables
- [ ] Bot is visible in Telegram (search for bot username)
- [ ] Railway service shows "Running" status
- [ ] Railway logs show "Telegram bot started"
- [ ] No error messages in Railway logs
- [ ] Bot responds to `/help` command

## Expected Behavior

When working correctly:
1. Bot should respond to `/help` immediately (no auth required)
2. Bot should respond to `/start` if Chat ID matches
3. Bot should show "Unauthorized access" if Chat ID doesn't match
4. Railway logs should show command received messages

