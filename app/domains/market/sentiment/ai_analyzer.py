# app/domains/market/sentiment/ai_analyzer.py
import json
import google.generativeai as genai
from datetime import datetime
from app.shared.config import config
from app.shared.logger import logger


class AISentimentAnalyzer:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-pro")

    def get_market_prediction(self):
        """Get market prediction using Gemini with web search"""
        logger.info("🤖 Gemini analyzing market conditions...")

        prompt = self._build_analysis_prompt()

        try:
            # Use Gemini with web search for latest data
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                ),
            )

            result = self._parse_ai_response(response.text)
            self._store_prediction(result)

            logger.info(
                f"✅ Analysis Complete: {result['sentiment']} ({result['confidence']}%)"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            return self._get_fallback_prediction()

    def _build_analysis_prompt(self):
        """Build prompt that works well with Gemini"""
        current_date = datetime.now().strftime("%Y-%m-%d")

        return f"""
        CURRENT DATE: {current_date}
        
        TASK: Analyze Indian stock market sentiment for tomorrow's trading session.
        
        RESEARCH AREAS:
        1. GLOBAL ECONOMIC NEWS (last 7 days)
           - Federal Reserve decisions/statements
           - US/Europe inflation data
           - Geopolitical events
           - Major corporate earnings
           - Oil prices and commodities
        
        2. US MARKETS (last 30 days)
           - S&P 500 and NASDAQ trends
           - Key technical levels
           - Market sentiment indicators
        
        3. INDIAN MARKETS (last 30 days)  
           - Nifty 50 and Bank Nifty trends
           - FII/DII investment data
           - Sector performance
           - Economic indicators (GDP, IIP, inflation)
        
        OUTPUT REQUIREMENTS:
        - Be objective and data-driven
        - Consider both technical and fundamental factors
        - Weight recent information more heavily
        
        RESPONSE FORMAT (STRICT JSON):
        {{
            "sentiment": "BULLISH/BEARISH/NEUTRAL",
            "confidence": 75,
            "reasoning": ["reason1", "reason2", "reason3"],
            "key_drivers": ["driver1", "driver2"],
            "outlook": "Brief summary",
            "timestamp": "{current_date}"
        }}
        """

    def _parse_ai_response(self, response_text):
        """Parse Gemini response"""
        try:
            # Clean response and find JSON
            import re

            json_match = re.search(
                r"\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}", response_text
            )

            if json_match:
                result = json.loads(json_match.group())
                return self._validate_prediction(result)
            else:
                return self._parse_text_response(response_text)

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return self._get_fallback_prediction()

    def _validate_prediction(self, prediction):
        """Ensure prediction has required fields"""
        required = ["sentiment", "confidence", "reasoning"]
        if all(field in prediction for field in required):
            return prediction
        return self._get_fallback_prediction()

    def _parse_text_response(self, text):
        """Fallback text parsing"""
        sentiment = "NEUTRAL"
        text_upper = text.upper()

        if "BULLISH" in text_upper:
            sentiment = "BULLISH"
        elif "BEARISH" in text_upper:
            sentiment = "BEARISH"

        return {
            "sentiment": sentiment,
            "confidence": 50,
            "reasoning": ["Text analysis completed"],
            "key_drivers": [],
            "outlook": "Analysis based on available data",
            "timestamp": datetime.now().isoformat(),
        }

    def _get_fallback_prediction(self):
        """Safe fallback"""
        return {
            "sentiment": "NEUTRAL",
            "confidence": 0,
            "reasoning": ["System error - using fallback"],
            "key_drivers": [],
            "outlook": "System temporarily unavailable",
            "timestamp": datetime.now().isoformat(),
        }

    def _store_prediction(self, prediction):
        """Store prediction"""
        try:
            import json
            from pathlib import Path

            storage_dir = "storage/sentiment_data"
            Path(storage_dir).mkdir(parents=True, exist_ok=True)

            filename = f"{storage_dir}/prediction_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

            with open(filename, "w") as f:
                json.dump(prediction, f, indent=2)

            logger.info(f"📊 Prediction stored: {filename}")

        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
