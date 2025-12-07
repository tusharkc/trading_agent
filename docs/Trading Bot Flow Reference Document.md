![[diagram-export-26-10-2025-17_00_59.png]]

---

## Daily Workflow Overview

### Morning Analysis Phase (7:00 AM - 9:15 AM)

**Objective**: Determine if market conditions favor trading

**Data Collection**:

- Global economic news from past 7 days
- US stock market performance data (30-day trend)
- Indian market performance data (30-day trend)

**AI Sentiment Analysis**:

- AI processes all data sources
- Outputs: BULLISH/BEARISH/NEUTRAL sentiment with confidence percentage
- Decision threshold: Proceed if BULLISH OR (NEUTRAL with ≥50% confidence)

### Stock Selection Phase (9:15 AM)

**Only executed if sentiment is favorable (BULLISH or NEUTRAL ≥50%)**

**Phase 2: Dynamic Sector Discovery & AI Selection**

**Step 1: Dynamic Sector Discovery**:

- Scans all NIFTY 500 stocks (~501 stocks)
- Validates each stock against financial criteria
- Groups qualifying stocks by sector
- Ranks sectors by number of qualifying stocks
- Returns top 10 sectors with most qualifying stocks

**Step 2: AI Sector Selection**:

- AI analyzes market sentiment and recent news
- Selects top 3 sectors from the discovered sectors
- Considers news momentum, technical strength, seasonal factors
- Uses actual market data (sectors with real qualifying stocks)

**Phase 3: Stock Selection**:

**Stock Filtering Criteria** (relaxed thresholds for better selection):

- **Trading Volume**: ≥ 50,000 (average daily volume)
- **EPS**: > 0 (positive trailing earnings per share)
- **Quarterly Growth**: ≥ -15% (allows cyclical recovery stocks)
- **Debt-to-Equity Ratio**: < 3.0 (includes financial services & capital-intensive sectors)
- **Operating Profit Margin**: > 5% (optional if data unavailable)
- **Market Capitalization**: ≥ 500 crores (includes mid-cap opportunities)

**Selection Process**:

- Uses pre-validated stocks from sector discovery (no LLM dependency)
- Flexible sector matching handles naming variations
- Ranks stocks by performance metric: `Volume × (1 + Profit Margin)`
- Selects top 3 stocks per sector
- **Total watchlist**: Up to 9 stocks (3 sectors × 3 stocks), may be fewer if sectors have limited qualifying stocks

### Trading Execution Phase (9:15 AM - 3:25 PM)

**Real-time monitoring at 5-minute intervals**

**Entry Conditions (ALL must be true)**:

- **Ichimoku Cloud**:
  - Price above cloud (bullish trend)
  - Tenkan-sen > Kijun-sen (momentum up)
  - Cloud color green (Senkou Span A > Senkou Span B)
- **MACD**:
  - MACD line > Signal line
  - Histogram > 0 and rising
- **Volume**: Current volume > 20-day average
- **Timing**: Signal occurs on 5-minute candle close

**Trade Execution**:

- Equal capital allocation across all selected stocks (up to 9 stocks)
- Immediate placement of:
  - Market buy order
  - Stop-loss order (2% below entry)
  - Take-profit order (4% above entry)

### Risk Management Framework

**Per-Trade Protection**:

- Stop-loss: 2% maximum loss per position
- Take-profit: 4% target gain per position
- Position sizing: Equal allocation across all selected stocks (up to 9 stocks)

**Portfolio Protection**:

- Maximum 9 simultaneous positions
- No overnight positions
- Daily stop-loss: 2% per trade
- Maximum daily portfolio drawdown: 18% (if all 9 positions hit stop-loss)
- Circuit breaker: Pause trading after 3 consecutive losses

### Exit Strategy

**Sell triggers (ANY condition met)**:

- Price hits 4% profit target
- Price hits 2% stop-loss
- Technical reversal signals:
  - Price closes below Ichimoku cloud
  - MACD line crosses below signal line
- Market close approaching (3:25 PM)

**End-of-Day Procedure**:

- 3:25 PM: Close all remaining positions
- No overnight holdings
- Daily performance analysis and logging

## System Architecture Principles

### Data Flow

```
News + Market Data → AI Sentiment Analysis → Sentiment Decision →
Dynamic Sector Discovery (Scan all NIFTY 500) → AI Sector Selection (Top 3) →
Stock Selection (Pre-validated stocks) → Watchlist Generation →
Technical Analysis → Trade Execution → Risk Management → Position Monitoring
```

### Stock Selection Architecture

**Two-Phase Approach**:

1. **Discovery Phase**: Scans all 501 NIFTY 500 stocks, validates against financial criteria, groups by sector
2. **Selection Phase**: AI picks top 3 sectors, system selects top 3 stocks per sector from pre-validated pool

**Key Features**:

- **No LLM dependency**: Uses actual market data validation
- **Dynamic sectors**: Discovers real sectors from market (no hardcoded mappings)
- **Efficient**: Reuses pre-validated stocks (no redundant API calls)
- **Flexible matching**: Handles sector name variations (e.g., "Financial Services" vs "Financial Services/Banking")

### Key Features

- **Multi-factor confirmation**: News + US data + India data alignment
- **Systematic execution**: Rule-based, emotion-free decisions
- **Risk-first approach**: Maximum loss limits built into every trade
- **Daily reset**: Fresh analysis each trading day
- **AI + Technical combo**: Fundamental analysis with technical timing
- **Dynamic sector discovery**: Scans all NIFTY 500 stocks to find actual market sectors
- **Data-driven selection**: Uses pre-validated stocks from market scanning (no LLM guessing)
- **Relaxed financial criteria**: Balanced thresholds to ensure sufficient stock selection while maintaining quality

### Success Metrics

- Win/Loss ratio tracking
- Average profit per trade
- Maximum drawdown monitoring
- AI sentiment accuracy validation
- System uptime and reliability
