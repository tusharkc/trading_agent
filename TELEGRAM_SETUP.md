# Telegram Bot Setup Guide

This guide will help you set up Telegram integration for your trading bot.

## Step 1: Create a Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts:
   - Choose a name for your bot (e.g., "My Trading Bot")
   - Choose a username (must end with 'bot', e.g., "my_trading_bot")
4. **Copy the bot token** - You'll receive something like:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
   ⚠️ **Keep this token secret!**

## Step 2: Get Your Chat ID

1. **Search for `@userinfobot`** in Telegram
2. Send `/start` to the bot
3. It will reply with your user information including your **Chat ID** (a number like `123456789`)
4. **Copy your Chat ID**

## Step 3: Configure Environment Variables

Add these to your `.env` file:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_step_1
TELEGRAM_CHAT_ID=your_chat_id_from_step_2
```

**Example:**
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## Step 4: Test Locally (Optional)

Before deploying, test the bot locally:

1. Make sure all environment variables are set in `.env`
2. Run:
   ```bash
   python bot_orchestrator.py
   ```
3. Open Telegram and find your bot (search for the username you created)
4. Send `/start` to your bot
5. Try commands like `/help`, `/status`

## Step 5: Deploy to Render

### Option A: Using Render Dashboard

1. **Go to [Render Dashboard](https://dashboard.render.com/)**
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `trading-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot_orchestrator.py`
5. **Add Environment Variables** (click "Environment" tab):
   - `DEEPSEEK_API_KEY` = (your key)
   - `NEWS_API_KEY` = (your key)
   - `ALPHA_VANTAGE_API_KEY` = (your key)
   - `KITE_API_KEY` = (your key)
   - `KITE_API_SECRET` = (your key)
   - `KITE_ACCESS_TOKEN` = (your key)
   - `TELEGRAM_BOT_TOKEN` = (from Step 1)
   - `TELEGRAM_CHAT_ID` = (from Step 2)
   - `TRADING_ENABLED` = `true`
   - `MAX_POSITIONS` = `9`
   - `POSITION_SIZE_PERCENT` = `11.11`
   - `PLACE_SL_TP_ORDERS` = `false`
   - `LOG_LEVEL` = `INFO`
6. Click **"Create Background Worker"**
7. Wait for deployment to complete

### Option B: Using render.yaml (Recommended)

1. **Push your code to GitHub** (including `render.yaml`)
2. **Go to Render Dashboard** → **"New +"** → **"Blueprint"**
3. **Connect your GitHub repository**
4. Render will automatically detect `render.yaml` and configure everything
5. **Add Environment Variables** in the dashboard (same as Option A)
6. Deploy!

## Step 6: Verify Deployment

1. Once deployed, check Render logs for:
   ```
   🤖 Telegram bot started
   ✅ Telegram bot thread started
   ```
2. Open Telegram and find your bot
3. Send `/start` - You should receive a welcome message
4. Try `/help` to see all commands

## Available Commands

Once your bot is running, you can use these commands in Telegram:

- `/start` - Start trading bot
- `/stop` - Stop trading bot
- `/status` - Get current bot status
- `/positions` - List all active positions
- `/balance` - Check account balance
- `/performance` - Today's performance summary
- `/watchlist` - Show current watchlist
- `/help` - Show help message

## Troubleshooting

### Bot doesn't respond

1. **Check Render logs** for errors
2. **Verify environment variables** are set correctly:
   - `TELEGRAM_BOT_TOKEN` should start with numbers
   - `TELEGRAM_CHAT_ID` should be a number
3. **Make sure you're messaging the correct bot** (check username)
4. **Check if Render service is running** (should show "Live" status)

### "Unauthorized access" error

- Your `TELEGRAM_CHAT_ID` doesn't match your Telegram user ID
- Re-check Step 2 to get the correct Chat ID

### Bot starts but trading doesn't work

- Check `TRADING_ENABLED=true` in environment variables
- Verify Kite API credentials are correct
- Check Render logs for Kite API errors

### Bot stops responding after some time

- Render free tier services sleep after inactivity
- The bot will wake up when you send a command
- Consider upgrading to paid tier for 24/7 uptime

## Security Notes

1. **Never commit `.env` file** to GitHub
2. **Keep your bot token secret** - anyone with it can control your bot
3. **Only you can use the bot** - Chat ID ensures only authorized access
4. **Use Render's environment variables** - Don't hardcode secrets

## Next Steps

1. Set up daily market analysis (runs automatically at 7 AM IST)
2. Monitor bot via Telegram commands
3. Receive notifications for trades and errors
4. Check daily performance via `/performance` command

## Support

If you encounter issues:
1. Check Render logs first
2. Verify all environment variables are set
3. Test bot locally before deploying
4. Check Telegram bot token and chat ID are correct

