# main.py - UPDATED VERSION
#!/usr/bin/env python3
"""
Trading Bot - AI Market Sentiment Prediction + Stock Selection
"""

import sys
import os

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.shared.config import config
from app.shared.logger import logger
from app.domains.market.sentiment.ai_analyzer import AISentimentAnalyzer
from app.domains.market.stock_selector import EnhancedStockSelector
from app.domains.market.watchlist_manager import WatchlistManager


def display_prediction(prediction):
    """Display prediction in readable format with safe field access"""
    print("\n" + "=" * 50)
    print("🎯 AI MARKET SENTIMENT PREDICTION")
    print("=" * 50)

    # Safe field access with defaults
    sentiment = prediction.get("sentiment", "UNKNOWN")
    confidence = prediction.get("confidence", 0)
    timestamp = prediction.get(
        "analysis_timestamp", prediction.get("timestamp", "Unknown")
    )

    print(f"Sentiment: {sentiment}")
    print(f"Confidence: {confidence}%")
    print(f"Timestamp: {timestamp}")

    # Reasoning with safe access
    reasoning = prediction.get("reasoning", [])
    if reasoning:
        print("\n📈 Key Reasoning:")
        for reason in reasoning:
            print(f"  • {reason}")
    else:
        print("\n📈 Key Reasoning: Not available")

    # Positive factors
    positive_factors = prediction.get("key_positive_factors", [])
    if positive_factors:
        print("\n✅ Positive Factors:")
        for factor in positive_factors:
            print(f"  • {factor}")

    # Negative factors
    negative_factors = prediction.get("key_negative_factors", [])
    if negative_factors:
        print("\n❌ Negative Factors:")
        for factor in negative_factors:
            print(f"  • {factor}")

    # Outlook summary
    outlook = prediction.get(
        "outlook_summary", prediction.get("outlook", "Not available")
    )
    print(f"\n📊 Outlook: {outlook}")
    print("=" * 50)


def display_watchlist(watchlist: dict, sectors: list):
    """Display final watchlist"""
    print("\n" + "=" * 50)
    print("📈 FINAL WATCHLIST")
    print("=" * 50)

    total_stocks = sum(len(stocks) for stocks in watchlist.values())
    print(f"✅ Total Stocks: {total_stocks} across {len(sectors)} sectors\n")

    for sector in sectors:
        stocks = watchlist.get(sector, [])
        print(f"🏷️  Sector: {sector}")
        if stocks:
            for i, stock in enumerate(stocks, 1):
                print(f"   {i}. {stock}")
        else:
            print("   ❌ No stocks found matching criteria")
        print()

    print("=" * 50)


def main():
    """Main trading bot application"""
    try:
        # Validate configuration
        config.validate()
        logger.info("✅ Configuration validated")

        # Initialize components
        analyzer = AISentimentAnalyzer()

        # Phase 1: AI Sentiment Analysis
        logger.info("🔄 Starting AI market analysis...")
        prediction = analyzer.get_market_prediction()
        display_prediction(prediction)

        # Trading decision
        sentiment = prediction.get("sentiment", "NEUTRAL")
        confidence = prediction.get("confidence", 0)

        if sentiment == "BULLISH" or sentiment == "NEUTRAL" and confidence >= 50:
            logger.info("🚀 Trading Decision: PROCEED - Market conditions favorable")

            # Phase 2: Sector Selection
            logger.info("\n🎯 Phase 2: Dynamic Sector Discovery & AI Selection...")
            selector = EnhancedStockSelector()

            # First, discover actual market sectors dynamically
            try:
                logger.info(
                    "📊 Step 1: Discovering actual sectors from NIFTY 500 stocks..."
                )
                # Get top 10 sectors from market (we'll let AI choose top 3 from these)
                market_sectors = selector.get_top_sectors_from_market(top_n=10)

                if market_sectors and len(market_sectors) >= 3:
                    logger.info(
                        f"✅ Found {len(market_sectors)} sectors with qualifying stocks in market"
                    )
                    # AI selects top 3 from actual market sectors
                    top_sectors = analyzer.get_top_sectors(
                        prediction, actual_market_sectors=market_sectors
                    )
                else:
                    logger.warning(
                        "⚠️  Could not discover market sectors, using AI-only selection"
                    )
                    top_sectors = analyzer.get_top_sectors(prediction)
            except Exception as e:
                logger.warning(
                    f"⚠️  Market sector discovery failed: {e}. Using AI-only selection."
                )
                top_sectors = analyzer.get_top_sectors(prediction)

            if not top_sectors:
                logger.error("❌ No sectors selected. Skipping stock selection.")
                top_sectors = []

            if top_sectors:
                logger.info(f"✅ Selected sectors: {', '.join(top_sectors)}")

                # Phase 3: Stock Selection
                logger.info("\n📊 Phase 3: Stock Selection...")
                watchlist = selector.select_stocks_with_mapping(top_sectors)

                # Display and save watchlist
                display_watchlist(watchlist, top_sectors)

                # Save watchlist for trading execution phase
                watchlist_manager = WatchlistManager()
                watchlist_manager.save_watchlist(watchlist, top_sectors, prediction)

                total_stocks = sum(len(stocks) for stocks in watchlist.values())
                if total_stocks > 0:
                    logger.info(
                        f"✅ Stock Selection Complete: {total_stocks} stocks in watchlist"
                    )
                    logger.info(
                        "🎯 Phase 2 & 3 Complete: Ready for Trading Execution Phase"
                    )

                    # Phase 4: Trading Execution (optional)
                    if config.TRADING_ENABLED:
                        logger.info("\n💹 Trading Execution Phase...")
                        logger.info(
                            "💡 To start trading execution, run: python trading_execution.py"
                        )
                        logger.info(
                            "   Or set up execution engine here to start automatically"
                        )
                    else:
                        logger.info(
                            "💡 Trading execution is disabled. Set TRADING_ENABLED=true to enable."
                        )
                else:
                    logger.info("⚠️  No stocks met the selection criteria")
            else:
                logger.error("❌ No sectors available for stock selection")

        else:
            logger.info("💤 Trading Decision: WAIT - Market conditions not optimal")
            logger.info("⏸️  Stock selection skipped due to unfavorable sentiment")

        logger.info("\n🎯 Trading Bot Analysis Complete!")

    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
