# app/domains/market/sentiment/ai_analyzer.py
import json
import re
from deepseek import DeepSeekAPI
from datetime import datetime
from app.shared.config import config
from app.shared.logger import logger
from app.domains.market.news_fetcher import NewsFetcher
from app.domains.market.market_data_fetcher import MarketDataFetcher


class AISentimentAnalyzer:
    def __init__(self):
        self.model = DeepSeekAPI(api_key=config.DEEPSEEK_API_KEY)
        self.news_fetcher = NewsFetcher()
        self.market_data_fetcher = MarketDataFetcher()

    def get_market_prediction(self):
        """Get market prediction using DeepSeek"""
        logger.info("🤖 DeepSeek analyzing market conditions...")

        prompt_content = self._build_analysis_prompt()
        messages = [
            {
                "role": "system",
                "content": "You are a financial analyst providing Indian stock market sentiment. Always respond with valid JSON in the specified format.",
            },
            {"role": "user", "content": prompt_content},
        ]

        try:
            response = self.model.chat_completion(
                messages=messages,
                model="deepseek-chat",
                temperature=0.1,
                max_tokens=2000,
            )

            # Debug the response structure
            print(f"📝 DeepSeek API Response: {response}")

            # Handle different response structures
            response_text = self._extract_response_text(response)
            print(f"📝 Extracted Response Text: {response_text}")

            result = self._parse_ai_response(response_text)
            self._store_prediction(result)

            logger.info(
                f"✅ Analysis Complete: {result['sentiment']} ({result['confidence']}%)"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            return self._get_fallback_prediction()

    def _extract_response_text(self, response):
        """Extract text from DeepSeek API response based on different possible structures"""
        try:
            # If response is a string (already the text content)
            if isinstance(response, str):
                return response

            # If response has a 'choices' attribute (OpenAI-like format)
            if hasattr(response, "choices"):
                return response.choices[0].message.content

            # If response is a dictionary
            if isinstance(response, dict):
                # Try different possible keys
                if "choices" in response:
                    return response["choices"][0]["message"]["content"]
                elif "content" in response:
                    return response["content"]
                elif "text" in response:
                    return response["text"]

            # If response has a 'to_dict' method
            if hasattr(response, "to_dict"):
                response_dict = response.to_dict()
                if "choices" in response_dict:
                    return response_dict["choices"][0]["message"]["content"]

            # Last resort: convert to string and try to extract JSON
            response_str = str(response)
            json_match = re.search(r"\{.*\}", response_str, re.DOTALL)
            if json_match:
                return json_match.group()

            return response_str

        except Exception as e:
            logger.error(f"Error extracting response text: {e}")
            return str(response)

    def _build_analysis_prompt(self):
        """Build prompt that works well with DeepSeek, incorporating fetched data"""
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Fetch news
        global_news = self.news_fetcher.fetch_news(
            "global economic news OR Federal Reserve OR inflation OR geopolitical OR corporate earnings OR oil prices",
            days=7,
        )
        us_market_news = self.news_fetcher.fetch_news(
            "US stock market OR S&P 500 OR NASDAQ", days=7
        )
        indian_market_news = self.news_fetcher.fetch_news(
            "Indian stock market OR Nifty 50 OR Bank Nifty OR FII DII OR Indian economy",
            days=7,
        )

        # Fetch market data
        us_market_data = self.market_data_fetcher.fetch_us_market_data(days=30)
        indian_market_data = self.market_data_fetcher.fetch_indian_market_data(
            symbol="NIFTY 50", days=30
        )

        # Format news for prompt
        formatted_global_news = "\n".join(
            [
                f"- {article['title']}: {article['description']}"
                for article in global_news[:5]
            ]
        )
        formatted_us_market_news = "\n".join(
            [
                f"- {article['title']}: {article['description']}"
                for article in us_market_news[:5]
            ]
        )
        formatted_indian_market_news = "\n".join(
            [
                f"- {article['title']}: {article['description']}"
                for article in indian_market_news[:5]
            ]
        )

        # Format market data for prompt
        formatted_us_market_data = "\n".join(
            [
                f"- {data['date']}: Open={data['open']}, Close={data['close']}, Volume={data['volume']}"
                for data in us_market_data[-5:]
            ]
        )
        formatted_indian_market_data = "\n".join(
            [
                f"- {data['date']}: Open={data['open']}, Close={data['close']}, Volume={data['volume']}"
                for data in indian_market_data[-5:]
            ]
        )

        return f"""
        CURRENT DATE: {current_date}
        
        TASK: Analyze Indian stock market sentiment for tomorrow's trading session based on the provided data.
        
        PROVIDED DATA:
        
        1. GLOBAL ECONOMIC NEWS (last 7 days):
        {formatted_global_news if formatted_global_news else "No global economic news found."}
        
        2. US MARKET NEWS (last 7 days):
        {formatted_us_market_news if formatted_us_market_news else "No US market news found."}
        
        3. INDIAN MARKET NEWS (last 7 days):
        {formatted_indian_market_news if formatted_indian_market_news else "No Indian market news found."}
        
        4. US MARKET DATA (last 30 days - showing last 5 entries):
        {formatted_us_market_data if formatted_us_market_data else "No US market data found."}
        
        5. INDIAN MARKET DATA (last 30 days - showing last 5 entries):
        {formatted_indian_market_data if formatted_indian_market_data else "No Indian market data found."}
        
        OUTPUT REQUIREMENTS:
        - Be objective and data-driven
        - Consider both technical and fundamental factors
        - Weight recent information more heavily
        - Respond ONLY with valid JSON, no additional text
        
        RESPONSE FORMAT (STRICT JSON - NO ADDITIONAL TEXT):
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
        """Parse DeepSeek response"""
        try:
            print(f"🔍 Parsing response: {response_text}")

            # Clean response and find JSON
            json_match = re.search(r"\{[\s\S]*\}", response_text)

            if json_match:
                json_str = json_match.group()
                print(f"🔍 Found JSON: {json_str}")

                # Clean up common formatting issues
                json_str = json_str.replace("```json", "").replace("```", "").strip()

                result = json.loads(json_str)
                validated_result = self._validate_prediction(result)

                if validated_result:
                    return validated_result

            # If JSON parsing fails, try text analysis
            return self._parse_text_response(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return self._parse_text_response(response_text)
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return self._get_fallback_prediction()

    def _validate_prediction(self, prediction):
        """Ensure prediction has required fields with proper types"""
        try:
            required = {
                "sentiment": str,
                "confidence": int,
                "reasoning": list,
                "key_drivers": list,
                "outlook": str,
                "timestamp": str,
            }

            # Check if all required fields exist
            if not all(field in prediction for field in required.keys()):
                return None

            # Validate sentiment value
            if prediction["sentiment"].upper() not in ["BULLISH", "BEARISH", "NEUTRAL"]:
                prediction["sentiment"] = "NEUTRAL"

            # Validate confidence range
            confidence = prediction["confidence"]
            if not isinstance(confidence, int) or confidence < 0 or confidence > 100:
                prediction["confidence"] = 50

            return prediction

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return None

    def _parse_text_response(self, text):
        """Fallback text parsing when JSON fails"""
        try:
            sentiment = "NEUTRAL"
            confidence = 50
            text_upper = text.upper()

            # Sentiment detection
            if "BULLISH" in text_upper:
                sentiment = "BULLISH"
                confidence = 70
            elif "BEARISH" in text_upper:
                sentiment = "BEARISH"
                confidence = 70

            # Extract reasoning from text
            reasoning = []
            if "reasoning" in text_upper:
                # Try to extract reasoning points
                lines = text.split("\n")
                for line in lines:
                    if any(keyword in line.upper() for keyword in ["•", "-", "REASON"]):
                        reasoning.append(line.strip("•- "))

            if not reasoning:
                reasoning = ["Analysis based on available market data"]

            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "reasoning": reasoning[:3],  # Limit to 3 reasons
                "key_drivers": [],
                "outlook": "Analysis completed based on available information",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Text parsing failed: {e}")
            return self._get_fallback_prediction()

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
