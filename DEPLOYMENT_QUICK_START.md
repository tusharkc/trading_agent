# Quick Start: Deploy to Render with Telegram

## What You Need to Provide

### 1. Telegram Bot Token (5 minutes)

1. Open Telegram → Search `@BotFather`
2. Send `/newbot`
3. Follow prompts to create bot
4. **Copy the token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Your Telegram Chat ID (2 minutes)

1. Open Telegram → Search `@userinfobot`
2. Send `/start`
3. **Copy your Chat ID** (a number like `123456789`)

### 3. Add to Environment Variables

Add these to your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Deploy to Render

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Add Telegram bot integration"
git push origin main
```

### Step 2: Deploy on Render

1. Go to [render.com](https://render.com) → Sign up/Login
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml`
5. **Add Environment Variables** (click "Environment" tab):

**Required:**
- `TELEGRAM_BOT_TOKEN` = (from Step 1 above)
- `TELEGRAM_CHAT_ID` = (from Step 2 above)
- `DEEPSEEK_API_KEY` = (your existing key)
- `NEWS_API_KEY` = (your existing key)
- `ALPHA_VANTAGE_API_KEY` = (your existing key)
- `KITE_API_KEY` = (your existing key)
- `KITE_API_SECRET` = (your existing key)
- `KITE_ACCESS_TOKEN` = (your existing key)

**Optional (already set in render.yaml):**
- `TRADING_ENABLED` = `true`
- `MAX_POSITIONS` = `9`
- `POSITION_SIZE_PERCENT` = `11.11`
- `PLACE_SL_TP_ORDERS` = `false`

6. Click **"Create Background Worker"**
7. Wait for deployment (~2-3 minutes)

### Step 3: Test Your Bot

1. Open Telegram → Find your bot (search the username you created)
2. Send `/start`
3. You should receive: "🤖 Trading Bot Started!"
4. Try `/help` to see all commands

## Available Commands

- `/start` - Start trading bot
- `/stop` - Stop trading bot  
- `/status` - Bot status & active positions
- `/positions` - List all active positions
- `/balance` - Account balance
- `/performance` - Today's performance
- `/watchlist` - Current watchlist
- `/help` - Show commands

## That's It! 🎉

Your bot is now running on Render and controllable via Telegram!

For detailed setup instructions, see `TELEGRAM_SETUP.md`

