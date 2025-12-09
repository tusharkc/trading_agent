# Trading Bot Flow Reference Document

## System Overview

An AI-powered intraday trading bot for Indian stock markets (NSE) that combines fundamental analysis, technical indicators, and risk management to execute automated trades. The system is **LONG-ONLY** (only buys stocks, no short selling) and operates during market hours (9:15 AM - 3:25 PM IST).

---

## Daily Workflow Overview

### Phase 1: Morning Analysis (7:00 AM - 9:15 AM)

**Objective**: Determine if market conditions favor trading

**Data Collection**:

- Global economic news from past 7 days (Federal Reserve, inflation, geopolitical events, corporate earnings, oil prices)
- US stock market performance data (30-day trend via Alpha Vantage API)
- Indian market performance data (30-day NIFTY 50 trend)

**AI Sentiment Analysis**:

- DeepSeek AI processes all data sources
- Outputs: **BULLISH** / **BEARISH** / **NEUTRAL** sentiment with confidence percentage
- Decision threshold: Proceed if **BULLISH** OR (**NEUTRAL** with ≥50% confidence)
- If sentiment is unfavorable, trading is skipped for the day

### Phase 2: Dynamic Sector Discovery & AI Selection (9:15 AM)

**Step 1: Dynamic Sector Discovery**:

- Scans all **NIFTY 500 stocks** (~501 stocks)
- Validates each stock against financial criteria:
  - **Trading Volume**: ≥ 50,000 (average daily volume)
  - **EPS**: > 0 (positive trailing earnings per share)
  - **Quarterly Growth**: ≥ -15% (allows cyclical recovery stocks)
  - **Debt-to-Equity Ratio**: < 3.0 (includes financial services & capital-intensive sectors)
  - **Operating Profit Margin**: > 5% (optional if data unavailable)
  - **Market Capitalization**: ≥ 500 crores (includes mid-cap opportunities)
- Groups qualifying stocks by sector
- Ranks sectors by number of qualifying stocks
- Returns top 9 sectors with most qualifying stocks
- Stores pre-validated stocks for reuse (no redundant API calls)

**Step 2: AI Sector Selection**:

- AI analyzes market sentiment and recent news
- Selects **top 3 sectors** from the discovered sectors
- Considers news momentum, technical strength, seasonal factors
- Uses actual market data (sectors with real qualifying stocks)

### Phase 3: Stock Selection (9:15 AM)

**Selection Process**:

- Uses pre-validated stocks from sector discovery (no LLM dependency)
- Flexible sector matching handles naming variations
- Ranks stocks by performance metric: `Volume × (1 + Profit Margin)`
- Selects **top 3 stocks per sector**
- **Total watchlist**: Up to **9 stocks** (3 sectors × 3 stocks), may be fewer if sectors have limited qualifying stocks
- Watchlist saved to `storage/watchlists/` for trading execution

### Phase 4: Trading Execution (9:15 AM - 3:25 PM IST)

**Real-time Monitoring**:

- WebSocket connection to Kite Connect for live market data
- Processes **5-minute candles** (candle closes trigger signal checks)
- Subscribes to all watchlist instruments for real-time updates

**Capital Management**:

- Automatically fetches available capital from Zerodha account on startup
- Priority order: `intraday_payin` → `cash` → `net` equity
- Raises error if capital is zero/negative or cannot be fetched
- No fallback to default values (must have valid account balance)

**Entry Conditions** (Flexible - requires **at least 2 out of 5** conditions):

- **Ichimoku Cloud**:
  - Price above cloud (bullish trend)
  - Tenkan-sen > Kijun-sen (momentum up)
  - Cloud color green (Senkou Span A > Senkou Span B)
- **MACD**:
  - MACD line > Signal line (bullish momentum)
  - Histogram > 0 and rising
- **Signal Strength Classification**:
  - **Strong**: 4-5 conditions met
  - **Moderate**: 3 conditions met
  - **Weak**: 2 conditions met (minimum threshold)

**Position Limits**:

- **Overall Portfolio**: Maximum `MAX_POSITIONS` (default: 9) simultaneous positions
- **Per-Stock**: Up to **6 positions per stock** (allows re-entry after exits)
- Position limit warnings logged only once when limit is first reached
- Warning flag resets when positions drop below limit

**Position Sizing**:

- Uses `POSITION_SIZE_PERCENT` (default: 11.11%) of total capital per trade
- Formula: `position_size = total_capital × (POSITION_SIZE_PERCENT / 100)`
- Quantity: `int(position_size / current_price)`
- If quantity ≤ 0, trade is skipped (common for high-priced stocks with low capital)

**Trade Execution Flow** (LONG-ONLY):

1. **Market BUY Order**: Places immediate market buy order
2. **Stop-Loss & Take-Profit Handling** (Configurable):
   - **Option A - Automatic Orders** (`PLACE_SL_TP_ORDERS=true`):
     - Places stop-loss order (SL-M) at 2% below entry price on Kite
     - Places take-profit order (LIMIT) at 4% above entry price on Kite
     - Orders consume margin but provide instant execution when levels hit
   - **Option B - Price Monitoring** (`PLACE_SL_TP_ORDERS=false`, default):
     - Calculates SL/TP levels but does NOT place orders on Kite (saves margin)
     - Bot monitors price every 5-minute candle and exits automatically when levels hit
     - SL/TP levels stored in database for manual monitoring
     - No margin consumed for pending orders
3. **Position Record**: Creates position record in database with entry price, quantity, SL, TP levels

**Tick Size Rounding**:

- All stop-loss and take-profit prices automatically rounded to instrument tick size
- Fetches tick size from Kite instruments API
- Handles floating-point precision issues
- Default tick size: 0.05 if not found (most NSE stocks)

**Exit Conditions** (Priority Order):

1. **Take-Profit** (Highest Priority):

   - Triggered when current price ≥ take-profit price (4% above entry)
   - Exit reason: `TAKE_PROFIT`
   - Position status: `CLOSED_PROFIT`

2. **Stop-Loss** (Highest Priority):

   - Triggered when current price ≤ stop-loss price (2% below entry)
   - Exit reason: `STOP_LOSS`
   - Position status: `CLOSED_LOSS`
   - **Execution Method**:
     - If `PLACE_SL_TP_ORDERS=true`: SL order on Kite triggers automatically (instant)
     - If `PLACE_SL_TP_ORDERS=false`: Bot detects on next 5-minute candle and places market SELL

3. **Technical Exits** (Only when position is losing money):

   - **MACD Reversal**: MACD line below signal line AND histogram meaningfully negative (< -0.1% of entry price)
     - Exit reason: `MACD_REVERSAL`
     - Position status: `CLOSED_REVERSAL`
   - **Price Below Cloud**: Price closes below Ichimoku cloud AND position losing > 0.5%
     - Exit reason: `PRICE_BELOW_CLOUD`
     - Position status: `CLOSED_REVERSAL`
   - **Important**: Technical exits only trigger if `pnl_percent < 0` (prevents cutting winners short)

4. **End-of-Day Square-Off** (3:25 PM):
   - All remaining positions closed at market price
   - Exit reason: `EOD`
   - Position status: `CLOSED_EOD`
   - No overnight positions allowed

**Exit Execution**:

- Cancels pending SL/TP orders (if tracked)
- Places market SELL order to exit position
- Updates position record with exit price, P&L, exit reason
- Updates performance metrics (win/loss tracking)

---

## Risk Management Framework

### Per-Trade Protection

- **Stop-Loss**: 2% maximum loss per position (automatically placed at broker)
- **Take-Profit**: 4% target gain per position (automatically placed at broker)
- **Position Sizing**: Configurable percentage of total capital per trade (default: 11.11%)
- **Tick Size Compliance**: All order prices rounded to instrument tick size

### Portfolio Protection

- **Maximum Positions**: `MAX_POSITIONS` simultaneous positions (default: 9)
- **Per-Stock Limit**: Up to 6 positions per stock (allows multiple entries)
- **No Overnight Positions**: All positions closed by 3:25 PM
- **Daily Drawdown Limit**: 18% maximum portfolio drawdown
  - Calculated as: `abs(portfolio_pnl / initial_capital) × 100`
  - Trading paused if drawdown exceeds 18%
- **Circuit Breaker**: Trading paused after **3 consecutive losses**
  - Tracks consecutive losses per trading day
  - Resets on first winning trade
  - Prevents further losses during losing streaks

### Risk Checks (Before Each Entry)

1. **Position Limit Check**: Verifies active positions < `MAX_POSITIONS`
2. **Per-Stock Limit Check**: Verifies active positions for stock < 6
3. **Circuit Breaker Check**: Verifies consecutive losses < 3
4. **Daily Drawdown Check**: Verifies portfolio drawdown < 18% (if negative P&L)

---

## System Architecture

### Core Components

1. **ExecutionEngine**: Main coordinator orchestrating all components
2. **KiteClient**: Zerodha Kite Connect API wrapper
   - Handles authentication, token management
   - Fetches historical data, quotes, instrument tokens
   - Places/cancels/modifies orders
   - Fetches available capital from account
   - Gets tick sizes for instruments
3. **WebSocketManager**: Real-time market data via Kite WebSocket
   - Aggregates ticks into 5-minute candles
   - Triggers callbacks on candle close
4. **TechnicalAnalyzer**: Calculates technical indicators
   - Ichimoku Cloud (Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span)
   - MACD (MACD line, Signal line, Histogram)
5. **SignalGenerator**: Evaluates entry/exit conditions
   - Entry: At least 2/5 conditions (flexible threshold)
   - Exit: Stop-loss, take-profit, technical reversals
6. **PositionManager**: Tracks positions in database
   - Creates/updates/closes positions
   - Calculates position size, stop-loss, take-profit
   - Rounds prices to tick size
7. **OrderManager**: Executes orders via Kite API
   - Market orders (BUY/SELL)
   - Stop-loss orders (SL-M)
   - Take-profit orders (LIMIT)
   - All prices rounded to tick size
8. **RiskManager**: Enforces risk limits
   - Position limits (overall and per-stock)
   - Circuit breaker (consecutive losses)
   - Daily drawdown limits
   - Performance tracking
9. **WatchlistManager**: Manages watchlist storage/retrieval

### Data Flow

```
News + Market Data → AI Sentiment Analysis → Sentiment Decision →
Dynamic Sector Discovery (Scan all NIFTY 500) → AI Sector Selection (Top 3) →
Stock Selection (Pre-validated stocks) → Watchlist Generation →
WebSocket Real-time Data → 5-Minute Candle Aggregation →
Technical Indicators (Ichimoku + MACD) → Signal Generation →
Risk Checks → Order Execution → Position Tracking → Exit Monitoring
```

### Database Schema

- **Positions**: Entry/exit prices, quantities, P&L, status, exit reasons
- **Orders**: Order IDs, types, status, timestamps
- **Trades**: Historical trade records
- **Performance**: Daily metrics (win rate, total P&L, consecutive losses, drawdown)

### Configuration (Environment Variables)

- `DEEPSEEK_API_KEY`: AI sentiment analysis
- `NEWS_API_KEY`: News data fetching
- `ALPHA_VANTAGE_API_KEY`: US market data
- `KITE_API_KEY`: Zerodha API key
- `KITE_API_SECRET`: Zerodha API secret
- `KITE_ACCESS_TOKEN`: Zerodha access token (regenerated daily)
- `TRADING_ENABLED`: Enable/disable live trading
- `MAX_POSITIONS`: Maximum simultaneous positions (default: 9)
- `POSITION_SIZE_PERCENT`: Capital allocation per trade (default: 11.11)
- `PLACE_SL_TP_ORDERS`: Place SL/TP orders on Kite (default: false)
  - `true`: Places SL/TP orders on Kite (consumes margin, instant execution)
  - `false`: Only monitors price levels (no margin, exits on next candle)
- `DATABASE_URL`: SQLite database path (default: `sqlite:///storage/trading.db`)
- `LOG_LEVEL`: Logging level (default: INFO)

---

## Key Features

### Trading Strategy

- **Long-Only**: Only BUY orders for entries (no short selling)
- **Intraday Only**: All positions closed by end of day (3:25 PM)
- **Multi-Position Per Stock**: Up to 6 positions per stock (allows re-entry)
- **Flexible Entry**: Requires at least 2/5 conditions (not all)
- **Smart Exits**: Technical exits only when losing (lets winners run)

### Technical Implementation

- **Tick Size Rounding**: All SL/TP prices automatically rounded to instrument tick size
- **Automatic Capital Fetching**: Fetches available capital from Zerodha account on startup
- **Configurable SL/TP Orders**: Can disable automatic SL/TP order placement to save margin
  - Default: Price monitoring only (no orders on Kite)
  - Optional: Place SL/TP orders on Kite for instant execution
- **Real-time Data**: WebSocket for live 5-minute candles
- **Historical Data**: Fetches 60+ days of historical data for indicator calculation
- **Error Handling**: Graceful handling of API timeouts, connection issues
- **Position Limit Warnings**: Logged once per limit breach (reduces log noise)

### Risk Controls

- **Multiple Position Limits**: Overall portfolio + per-stock limits
- **Circuit Breaker**: Automatic trading pause after 3 consecutive losses
- **Daily Drawdown Protection**: 18% maximum portfolio drawdown
- **Per-Trade Limits**: 2% stop-loss, 4% take-profit on every position

### Data Management

- **Watchlist Storage**: JSON files in `storage/watchlists/`
- **Sentiment Data**: JSON files in `storage/sentiment_data/`
- **Simulation Results**: CSV files in `storage/simulations/YYYYMMDD/`
- **Logs**: Daily log files in `logs/bot_YYYYMMDD.log`
- **Database**: SQLite for positions, orders, trades, performance

---

## Daily Operations

### Morning Setup (Before 9:15 AM)

1. **Generate Access Token**: Run `python generate_kite_token.py` (tokens expire daily)
2. **Check Balance**: Run `python check_balance.py` to verify account funds
3. **Run Analysis**: Execute `python main.py` to:
   - Fetch market sentiment
   - Discover sectors and select stocks
   - Generate watchlist

### Trading Hours (9:15 AM - 3:25 PM)

1. **Start Execution**: Run `python trading_execution.py`
2. **Monitor Logs**: Watch `logs/bot_YYYYMMDD.log` for:
   - Entry signals and executions
   - Exit signals and executions
   - Position limit warnings
   - Risk management alerts
3. **Automatic Operations**:
   - Real-time signal detection
   - Order placement and execution
   - Position tracking
   - Risk limit enforcement
   - End-of-day square-off (3:25 PM)

### End of Day

- All positions automatically closed at 3:25 PM
- Performance metrics updated
- Daily reset for next trading day

---

## Exit Reasons Reference

- `TAKE_PROFIT`: Price hit 4% profit target
- `STOP_LOSS`: Price hit 2% stop-loss
- `MACD_REVERSAL`: MACD reversal signal (only when losing)
- `PRICE_BELOW_CLOUD`: Price below Ichimoku cloud (only when losing > 0.5%)
- `EOD`: End-of-day square-off

---

## Success Metrics

- **Win Rate**: Percentage of profitable trades
- **Average Profit Per Trade**: Mean P&L per trade
- **Maximum Drawdown**: Worst portfolio drawdown
- **Consecutive Losses**: Tracked for circuit breaker
- **Total Daily P&L**: Sum of all trade P&Ls
- **Position Utilization**: Active positions vs. maximum allowed

---

## Important Notes

1. **Access Token**: Must be regenerated daily using `generate_kite_token.py`
2. **Capital Fetching**: System automatically fetches capital from account (no manual input)
3. **Long-Only**: System only places BUY orders for entries (SELL only for exits)
4. **SL/TP Orders**: By default, SL/TP orders are NOT placed on Kite (saves margin)
   - Set `PLACE_SL_TP_ORDERS=true` in `.env` to enable automatic SL/TP orders
   - Default behavior: Bot monitors price levels and exits automatically when hit
5. **Tick Size**: All SL/TP prices automatically rounded to prevent order rejections
6. **Position Limits**: Both overall (9) and per-stock (6) limits enforced
7. **Technical Exits**: Only trigger when position is losing (prevents cutting winners)
8. **End-of-Day**: All positions must be closed by 3:25 PM (no overnight holdings)
