# main.py - UPDATED VERSION
#!/usr/bin/env python3
"""
Trading Bot - AI Market Sentiment Prediction
"""

import sys
import os

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.shared.config import config
from app.shared.logger import logger
from app.domains.market.sentiment.ai_analyzer import AISentimentAnalyzer


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


def main():
    """Main trading bot application"""
    try:
        # Validate configuration
        config.validate()
        logger.info("✅ Configuration validated")

        # Initialize AI analyzer
        analyzer = AISentimentAnalyzer()

        # Get market prediction
        logger.info("🔄 Starting AI market analysis...")
        prediction = analyzer.get_market_prediction()

        # Display results
        display_prediction(prediction)

        # Trading decision with safe field access
        sentiment = prediction.get("sentiment", "NEUTRAL")
        confidence = prediction.get("confidence", 0)

        if sentiment == "BULLISH" and confidence >= 60:
            logger.info("🚀 Trading Decision: PROCEED - Market conditions favorable")
        else:
            logger.info("💤 Trading Decision: WAIT - Market conditions not optimal")

        logger.info("🎯 Phase 1 Complete: AI Sentiment Analysis Working!")

    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
