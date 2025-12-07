import yfinance as yf
import nsepython
from typing import List, Dict, Any
import time
import json
import re
from datetime import datetime

from app.shared.config import config
from app.shared.logger import logger


class StockSelector:
    """
    Selects stocks based on financial criteria for given sectors using nsepython.
    """

    def __init__(self):
        """Initialize the stock selector with cache for discovered stocks."""
        self._discovered_stocks_by_sector = {}  # Cache for pre-validated stocks

    def _get_nifty_500_stocks(self) -> List[str]:
        """Fetches the list of NIFTY 500 stock symbols using nsetools dynamically.

        Raises:
            ImportError: If nsetools is not installed
            RuntimeError: If fetching from NSE fails or returns insufficient data
        """
        print("📋 Fetching NIFTY 500 constituents dynamically...")

        try:
            from nsetools import Nse
        except ImportError as e:
            error_msg = (
                "nsetools library is not installed. "
                "Please install it with: pip install nsetools"
            )
            print(f"❌ {error_msg}")
            raise ImportError(error_msg) from e

        try:
            nse = Nse()
            # Get NIFTY 500 constituents - returns a list of stock symbols
            symbols = nse.get_stocks_in_index("NIFTY 500")

            if not symbols:
                error_msg = (
                    "Failed to fetch NIFTY 500 constituents: Empty response from NSE"
                )
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            # Ensure it's a list of strings
            if not isinstance(symbols, list):
                error_msg = (
                    f"Unexpected data type from NSE: expected list, got {type(symbols)}"
                )
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            # Filter to ensure all items are strings
            symbols = [s for s in symbols if isinstance(s, str) and s.strip()]

            if len(symbols) < 100:
                error_msg = (
                    f"Insufficient stocks fetched from NSE: got {len(symbols)} stocks, "
                    f"expected at least 100. This may indicate an API issue."
                )
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            print(f"✅ Fetched {len(symbols)} stocks dynamically from NSE")
            return symbols

        except (ImportError, RuntimeError):
            # Re-raise ImportError and RuntimeError as-is
            raise
        except Exception as e:
            error_msg = f"Error fetching NIFTY 500 constituents from NSE: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg) from e

    def _get_stock_details(self, ticker: str) -> Any:
        """Fetches fundamental data for a single stock ticker using yfinance."""
        try:
            # For Indian stocks, append .NS for yfinance
            yf_ticker = f"{ticker}.NS"
            stock = yf.Ticker(yf_ticker)

            # Test if stock exists by trying to get info with timeout
            info = stock.info
            if not info:
                return None

            return stock
        except Exception:
            # Error fetching stock data - return None to skip this stock
            return None

    def _meets_criteria(
        self, stock: Any, target_sectors: List[str], ticker: str = ""
    ) -> bool:
        """
        Checks if a stock meets the predefined financial criteria.
        Returns True if all criteria pass, False otherwise with detailed logging.
        """
        try:
            info = stock.info
            stock_name = ticker or stock.ticker.replace(".NS", "")

            # 1. Sector Check
            sector = info.get("sector", "").upper() if info.get("sector") else ""
            target_sectors_upper = [s.upper() for s in target_sectors]

            if not sector:
                print("    ❌ FAILED: No sector information available")
                logger.info(f"  ❌ {stock_name}: Failed - No sector data")
                return False

            # Flexible sector matching - check if sector matches any target sector
            # Supports partial matches and case-insensitive comparison
            sector_match = False
            for target_sector in target_sectors_upper:
                # Direct match
                if target_sector == sector:
                    sector_match = True
                    break
                # Check if one contains the other (for flexible matching)
                if target_sector in sector or sector in target_sector:
                    sector_match = True
                    break
                # Normalize both for better matching (remove spaces, special chars)
                target_normalized = (
                    target_sector.replace(" ", "").replace("-", "").replace("&", "")
                )
                sector_normalized = (
                    sector.replace(" ", "").replace("-", "").replace("&", "")
                )
                if (
                    target_normalized in sector_normalized
                    or sector_normalized in target_normalized
                ):
                    sector_match = True
                    break

            if not sector_match:
                print(
                    f"    ❌ FAILED: Sector mismatch - Stock sector: '{sector}', Target sectors: {target_sectors}"
                )
                logger.info(
                    f"  ❌ {stock_name}: Failed - Sector '{sector}' not in {target_sectors}"
                )
                return False

            # 2. Volume Check (relaxed for more liquidity options)
            avg_volume = info.get("averageVolume", 0)
            if avg_volume < 50000:  # Reduced from 100,000 to 50,000
                print(f"    ❌ FAILED: Low volume - {avg_volume:,} < 50,000 required")
                logger.info(
                    f"  ❌ {stock_name}: Failed - Volume {avg_volume:,} below 50,000 threshold"
                )
                return False

            # 3. Profitability Check - Use trailing EPS
            trailing_eps = info.get("trailingEps")
            if trailing_eps is None:
                print("    ❌ FAILED: No EPS data available")
                logger.info(f"  ❌ {stock_name}: Failed - No EPS data")
                return False
            if trailing_eps <= 0:
                print(f"    ❌ FAILED: Negative EPS - {trailing_eps:.2f} (must be > 0)")
                logger.info(
                    f"  ❌ {stock_name}: Failed - EPS {trailing_eps:.2f} is not positive"
                )
                return False

            # 3a. Quarterly Profit Growth (YoY) Check - RELAXED
            # Allow stocks with slight negative growth (up to -15%) for cyclical recovery
            growth_failed = False
            try:
                earnings_quarterly_growth = info.get("earningsQuarterlyGrowth")
                if (
                    earnings_quarterly_growth is not None
                    and earnings_quarterly_growth < -0.15  # Allow up to -15% decline
                ):
                    print(
                        f"    ❌ FAILED: Very negative quarterly growth - {earnings_quarterly_growth:.1%} < -15% (must be >= -15%)"
                    )
                    logger.info(
                        f"  ❌ {stock_name}: Failed - Quarterly growth {earnings_quarterly_growth:.1%} is below -15% threshold"
                    )
                    growth_failed = True
                else:
                    # If not available, check earnings growth
                    earnings_growth = info.get("earningsGrowth")
                    if (
                        earnings_growth is not None and earnings_growth < -0.15
                    ):  # Allow up to -15%
                        print(
                            f"    ❌ FAILED: Very negative earnings growth - {earnings_growth:.1%} < -15% (must be >= -15%)"
                        )
                        logger.info(
                            f"  ❌ {stock_name}: Failed - Earnings growth {earnings_growth:.1%} is below -15% threshold"
                        )
                        growth_failed = True
            except Exception:
                # If we can't verify growth, skip this check (data might not be available)
                logger.info(
                    f"  ℹ️  {stock_name}: Could not verify growth data (skipping check)"
                )

            if growth_failed:
                return False

            # 4. Debt-to-Equity Ratio Check - RELAXED
            # Increased threshold to allow financial services and capital-intensive sectors
            debt_to_equity = info.get("debtToEquity")
            if debt_to_equity is None:
                print("    ❌ FAILED: No Debt-to-Equity data available")
                logger.info(f"  ❌ {stock_name}: Failed - No D/E ratio data")
                return False
            if debt_to_equity >= 3.0:  # Increased from 1.5 to 3.0
                print(
                    f"    ❌ FAILED: High D/E ratio - {debt_to_equity:.2f} >= 3.0 (must be < 3.0)"
                )
                logger.info(
                    f"  ❌ {stock_name}: Failed - D/E ratio {debt_to_equity:.2f} exceeds 3.0"
                )
                return False

            # 5. Operating Profit Margin Check - RELAXED
            # Reduced threshold and allow missing data for some sectors
            operating_margin = info.get("operatingMargins")
            if operating_margin is None:
                # Allow missing margin data - just log warning
                logger.info(
                    f"  ℹ️  {stock_name}: Operating margin data not available (allowing stock)"
                )
            elif operating_margin <= 0.05:  # Reduced from 8% (0.08) to 5% (0.05)
                print(
                    f"    ❌ FAILED: Low operating margin - {operating_margin:.1%} <= 5% (must be > 5%)"
                )
                logger.info(
                    f"  ❌ {stock_name}: Failed - Operating margin {operating_margin:.1%} below 5% threshold"
                )
                return False

            # 6. Market Cap Check - RELAXED
            # Reduced threshold to include more mid-cap stocks
            market_cap = info.get("marketCap")
            if market_cap is None:
                print("    ❌ FAILED: No market cap data available")
                logger.info(f"  ❌ {stock_name}: Failed - No market cap data")
                return False
            market_cap_crore = market_cap / 10000000  # Convert to crores
            if market_cap < 500000000:  # Reduced from 1000 crores to 500 crores
                print(
                    f"    ❌ FAILED: Market cap too small - {market_cap_crore:.0f} crore < 500 crore required"
                )
                logger.info(
                    f"  ❌ {stock_name}: Failed - Market cap {market_cap_crore:.0f} crore below 500 crore"
                )
                return False

            # All criteria passed
            print("    ✅ PASSED: All criteria met")
            operating_margin_display = (
                f"{operating_margin:.1%}" if operating_margin else "N/A"
            )
            print(
                f"       Sector: {sector}, Volume: {avg_volume:,}, D/E: {debt_to_equity:.2f}, Op Margin: {operating_margin_display}, Market Cap: {market_cap_crore:.0f} crore"
            )
            logger.info(
                f"  ✅ {stock_name}: PASSED - All criteria met (Sector: {sector})"
            )
            return True

        except Exception as e:
            error_msg = f"Error evaluating criteria: {str(e)}"
            print(f"    ❌ FAILED: Exception during evaluation - {error_msg}")
            logger.error(f"  ❌ {ticker or 'Unknown'}: Failed - {error_msg}")
            return False

    def get_top_sectors_from_market(self, top_n: int = 3) -> List[str]:
        """
        Dynamically discover top sectors from NIFTY 500 stocks based on number of qualifying stocks.
        Returns the top N sectors that have the most stocks meeting financial criteria.
        """
        logger.info(f"🔍 Discovering top {top_n} sectors from actual market data...")

        try:
            # Get all NIFTY 500 stocks
            all_stocks = self._get_nifty_500_stocks()
            logger.info(f"📊 Analyzing {len(all_stocks)} stocks from NIFTY 500...")

            # Extract sectors and count qualifying stocks per sector
            sector_qualifying_count = {}  # {sector: count of qualifying stocks}
            sector_stocks_map = {}  # {sector: [list of stock objects]}

            processed = 0
            for ticker in all_stocks:
                processed += 1
                if processed % 50 == 0:
                    logger.info(f"  Processed {processed}/{len(all_stocks)} stocks...")

                stock_details = self._get_stock_details(ticker)
                if not stock_details:
                    continue

                try:
                    info = stock_details.info
                    sector = (
                        info.get("sector", "").strip() if info.get("sector") else ""
                    )

                    if not sector:
                        continue

                    # Check if stock meets criteria (without sector filter)
                    # We'll check all criteria except sector matching
                    if self._stock_meets_financial_criteria(stock_details, ticker):
                        if sector not in sector_qualifying_count:
                            sector_qualifying_count[sector] = 0
                            sector_stocks_map[sector] = []

                        sector_qualifying_count[sector] += 1
                        sector_stocks_map[sector].append(stock_details)

                except Exception:
                    continue

                time.sleep(0.05)  # Small delay to avoid rate limiting

            if not sector_qualifying_count:
                logger.warning("⚠️  No sectors found with qualifying stocks")
                self._discovered_stocks_by_sector = {}
                return []

            # Store discovered stocks for reuse (avoid re-fetching and re-validating)
            self._discovered_stocks_by_sector = sector_stocks_map
            total_discovered = sum(len(stocks) for stocks in sector_stocks_map.values())
            logger.info(f"💾 Stored {total_discovered} pre-validated stocks for reuse")

            # Sort sectors by number of qualifying stocks (descending)
            sorted_sectors = sorted(
                sector_qualifying_count.items(), key=lambda x: x[1], reverse=True
            )

            top_sectors = [sector for sector, count in sorted_sectors[:top_n]]

            logger.info(f"✅ Top {len(top_sectors)} sectors discovered:")
            for sector, count in sorted_sectors[:top_n]:
                logger.info(f"  📈 {sector}: {count} qualifying stocks")

            return top_sectors

        except Exception as e:
            logger.error(f"❌ Failed to discover sectors from market: {e}")
            raise RuntimeError(
                f"Could not discover sectors from market: {str(e)}"
            ) from e

    def _stock_meets_financial_criteria(self, stock: Any, ticker: str = "") -> bool:
        """
        Checks if a stock meets financial criteria (excluding sector check).
        This is used for sector discovery.
        """
        try:
            info = stock.info

            # 2. Volume Check (relaxed for more liquidity options)
            avg_volume = info.get("averageVolume", 0)
            if avg_volume < 50000:  # Reduced from 100,000 to 50,000
                return False

            # 3. Profitability Check - Use trailing EPS
            trailing_eps = info.get("trailingEps")
            if trailing_eps is None or trailing_eps <= 0:
                return False

            # 3a. Quarterly Profit Growth (YoY) Check - RELAXED
            # Allow stocks with slight negative growth (up to -15%) for cyclical recovery
            try:
                earnings_quarterly_growth = info.get("earningsQuarterlyGrowth")
                if (
                    earnings_quarterly_growth is not None
                    and earnings_quarterly_growth < -0.15  # Allow up to -15% decline
                ):
                    return False
                # If not available, check earnings growth
                earnings_growth = info.get("earningsGrowth")
                if (
                    earnings_growth is not None and earnings_growth < -0.15
                ):  # Allow up to -15%
                    return False
            except Exception:
                pass  # If growth data unavailable, skip check

            # 4. Debt-to-Equity Ratio Check - RELAXED
            # Increased threshold to allow financial services and capital-intensive sectors
            debt_to_equity = info.get("debtToEquity")
            if debt_to_equity is None:
                return False  # Still require D/E data if available
            if debt_to_equity >= 3.0:  # Increased from 1.5 to 3.0
                return False

            # 5. Operating Profit Margin Check - RELAXED
            # Reduced threshold and allow missing data for some sectors
            operating_margin = info.get("operatingMargins")
            if operating_margin is None:
                # Allow missing margin data if other criteria pass
                pass
            elif operating_margin <= 0.05:  # Reduced from 8% (0.08) to 5% (0.05)
                return False

            # 6. Market Cap Check - RELAXED
            # Reduced threshold to include more mid-cap stocks
            market_cap = info.get("marketCap")
            if market_cap is None:
                return False
            if market_cap < 500000000:  # Reduced from 1000 crores to 500 crores
                return False

            return True

        except Exception:
            return False

    def _get_stock_performance_metric(self, stock: Any) -> float:
        """
        Get a performance metric for ranking stocks.
        Uses volume * profit margin as ranking criteria.
        """
        try:
            info = stock.info
            volume = info.get("averageVolume", 0)
            profit_margin = info.get("profitMargins", 0) or info.get(
                "operatingMargins", 0
            )

            return volume * (1 + profit_margin)  # Higher is better
        except Exception:
            return 0

    def _get_sector_from_nse(self, symbol: str) -> str:
        """
        Get sector information from NSE using nsepython.
        """
        try:
            # Get stock info from NSE
            quote = nsepython.quote(symbol)
            industry = quote.get("industry", "")
            return industry
        except Exception:
            # Could not get NSE sector data
            return ""

    def _get_llm_stock_suggestions(self, sectors: List[str]) -> Dict[str, List[str]]:
        """
        Uses LLM with internet search to suggest stocks in sectors that match financial criteria.

        Raises:
            RuntimeError: If LLM fails to provide suggestions
        """
        from deepseek import DeepSeekAPI

        logger.info(
            f"🤖 Using AI with internet search to suggest stocks for sectors: {sectors}"
        )

        current_date = datetime.now().strftime("%Y-%m-%d")

        # Get NIFTY 500 list for context (optional but helpful)
        try:
            from nsetools import Nse

            nse = Nse()
            nifty_500_stocks = nse.get_stocks_in_index("NIFTY 500")
            stocks_sample = (
                ", ".join(nifty_500_stocks[:50])
                if len(nifty_500_stocks) > 50
                else ", ".join(nifty_500_stocks)
            )
            stocks_context = f"\nReference: Sample NIFTY 500 stocks: {stocks_sample}... (total {len(nifty_500_stocks)} stocks)"
        except Exception:
            stocks_context = ""

        financial_criteria = """
        Financial Criteria (ALL must be met):
        1. High trading volume (average volume > 100,000)
        2. Positive earnings per share (EPS > 0)
        3. Positive quarterly profit growth (YoY) or at least non-negative earnings growth
        4. Debt-to-Equity ratio < 1.5
        5. Operating profit margin > 8%
        6. Market capitalization > 1000 crore (10 billion INR)
        """

        prompt = f"""
        CURRENT DATE: {current_date}
        {stocks_context}
        
        TASK: Use internet search to find current information and suggest Indian NSE stocks that belong to 
        the following sectors AND meet ALL the financial criteria below.
        
        TARGET SECTORS:
        {chr(10).join(f"- {sector}" for sector in sectors)}
        
        {financial_criteria}
        
        CRITICAL REQUIREMENTS:
        1. USE INTERNET SEARCH to find the most current financial data and company information
        2. Search for recent financial reports, earnings, debt ratios, and profit margins
        3. Focus ONLY on NIFTY 500 listed stocks (major Indian companies traded on NSE)
        4. For each sector, suggest 5-10 stocks that you can verify meet ALL financial criteria
        5. Use correct NSE stock symbols (e.g., RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, MARUTI, ITC)
        6. Prioritize large-cap, financially healthy companies with strong fundamentals
        7. DO NOT guess - only suggest stocks you can verify through search meet the criteria
        
        SEARCH STRATEGY:
        - Search for: "top [sector] stocks India NSE financials 2024"
        - Search for: "[company name] debt equity ratio operating margin 2024"
        - Search for: "best [sector] stocks India strong fundamentals low debt"
        - Verify each stock meets: volume > 100k, EPS > 0, D/E < 1.5, margin > 8%, market cap > 1000 crore
        
        RESPONSE FORMAT (STRICT JSON - NO ADDITIONAL TEXT):
        {{
            "{sectors[0] if sectors else "Sector1"}": ["STOCK1", "STOCK2", "STOCK3", "STOCK4", "STOCK5"],
            "{sectors[1] if len(sectors) > 1 else "Sector2"}": ["STOCK1", "STOCK2", "STOCK3"],
            "{sectors[2] if len(sectors) > 2 else "Sector3"}": ["STOCK1", "STOCK2", "STOCK3"]
        }}
        
        Use the EXACT sector names provided above as JSON keys.
        Return 5-10 stock symbols per sector that you verified meet ALL criteria through internet search.
        """

        try:
            model = DeepSeekAPI(api_key=config.DEEPSEEK_API_KEY)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert Indian stock market analyst with access to current financial data. "
                        "Use internet search to find the most accurate, up-to-date information about Indian stocks. "
                        "Always respond with valid JSON only, no additional text."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            response = model.chat_completion(
                messages=messages,
                model="deepseek-chat",
                temperature=0.1,
                max_tokens=2000,
            )

            response_text = self._extract_llm_response_text(response)
            suggestions = self._parse_stock_suggestions(response_text, sectors)

            logger.info(
                f"✅ AI suggested {sum(len(s) for s in suggestions.values())} stocks across {len(sectors)} sectors"
            )
            return suggestions

        except Exception as e:
            error_msg = f"Failed to get stock suggestions from AI: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(error_msg) from e

    def _extract_llm_response_text(self, response) -> str:
        """Extract text from LLM response"""
        try:
            if isinstance(response, str):
                return response

            if hasattr(response, "choices"):
                return response.choices[0].message.content

            if isinstance(response, dict):
                if "choices" in response:
                    return response["choices"][0]["message"]["content"]
                elif "content" in response:
                    return response["content"]
                elif "text" in response:
                    return response["text"]

            if hasattr(response, "to_dict"):
                response_dict = response.to_dict()
                if "choices" in response_dict:
                    return response_dict["choices"][0]["message"]["content"]

            response_str = str(response)
            json_match = re.search(r"\{.*\}", response_str, re.DOTALL)
            if json_match:
                return json_match.group()

            return response_str

        except Exception as e:
            logger.error(f"Error extracting LLM response text: {e}")
            return str(response)

    def _parse_stock_suggestions(
        self, response_text: str, sectors: List[str]
    ) -> Dict[str, List[str]]:
        """Parse and validate LLM stock suggestions"""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            json_str = (
                json_match.group().replace("```json", "").replace("```", "").strip()
            )
            result = json.loads(json_str)

            # Validate structure
            suggestions = {}
            for sector in sectors:
                stocks = result.get(sector, [])
                if isinstance(stocks, list):
                    # Clean and filter stock symbols
                    cleaned_stocks = [
                        str(s).strip().upper()
                        for s in stocks
                        if s and isinstance(s, (str, int))
                    ]
                    suggestions[sector] = cleaned_stocks[
                        :10
                    ]  # Limit to top 10 per sector
                else:
                    suggestions[sector] = []

            # Validate we got suggestions
            total_suggestions = sum(len(s) for s in suggestions.values())
            if total_suggestions == 0:
                raise ValueError("LLM returned no stock suggestions")

            return suggestions

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON from LLM response: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Error parsing stock suggestions: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg) from e

    def _sectors_match(self, sector1: str, sector2: str) -> bool:
        """
        Helper to check if two sector names match (flexible matching).
        Handles variations like "Financial Services" vs "Financial Services/Banking".
        """
        if not sector1 or not sector2:
            return False

        s1 = (
            sector1.upper()
            .replace(" ", "")
            .replace("-", "")
            .replace("&", "")
            .replace("/", "")
        )
        s2 = (
            sector2.upper()
            .replace(" ", "")
            .replace("-", "")
            .replace("&", "")
            .replace("/", "")
        )

        # Exact match after normalization
        if s1 == s2:
            return True

        # Check if one contains the other
        if s1 in s2 or s2 in s1:
            return True

        return False

    def select_stocks(self, sectors: List[str]) -> Dict[str, List[str]]:
        """
        Selects the top 3 stocks for each given sector using pre-discovered stocks.
        Uses stocks that were already validated during sector discovery.
        Requires get_top_sectors_from_market() to be called first to populate discovered stocks.
        """
        eligible_stocks = {sector: [] for sector in sectors}

        # Use pre-discovered stocks (from get_top_sectors_from_market)
        if self._discovered_stocks_by_sector:
            total_discovered = sum(
                len(stocks) for stocks in self._discovered_stocks_by_sector.values()
            )
            logger.info(
                f"\n✅ Using {total_discovered} pre-validated stocks from sector discovery"
            )
            logger.info(f"📊 Selecting stocks for sectors: {sectors}")

            for sector in sectors:
                matching_stocks = []

                # Find matching sectors using flexible matching
                for (
                    discovered_sector,
                    stocks,
                ) in self._discovered_stocks_by_sector.items():
                    if self._sectors_match(discovered_sector, sector):
                        matching_stocks.extend(stocks)
                        logger.info(
                            f"  📌 Matched '{sector}' with discovered sector '{discovered_sector}' ({len(stocks)} stocks)"
                        )

                # Re-validate with sector filter (stocks already passed financial criteria)
                # This double-check ensures sector name matches exactly
                for stock in matching_stocks:
                    try:
                        ticker = stock.ticker.replace(".NS", "")
                        if self._meets_criteria(stock, [sector], ticker=ticker):
                            eligible_stocks[sector].append(stock)
                    except Exception as e:
                        logger.debug(f"  ⚠️  Error re-validating {stock.ticker}: {e}")
                        continue

                if eligible_stocks[sector]:
                    logger.info(
                        f"  ✅ {sector}: Found {len(eligible_stocks[sector])} qualifying stocks"
                    )
                else:
                    logger.info(
                        f"  ⚠️  {sector}: No stocks matched from discovered stocks"
                    )
        else:
            # No pre-discovered stocks available - return empty watchlist
            logger.warning(
                f"\n⚠️  No pre-discovered stocks available. "
                f"Please call get_top_sectors_from_market() first to discover and validate stocks. "
                f"Returning empty watchlist for sectors: {sectors}"
            )
            for sector in sectors:
                logger.info(
                    f"  ❌ {sector}: No stocks available (sector discovery not performed)"
                )

        # Sort and select top 3 per sector
        final_watchlist = {}
        for sector, stocks in eligible_stocks.items():
            if stocks:
                # Sort by performance metric
                stocks.sort(key=self._get_stock_performance_metric, reverse=True)
                # Select top 3
                top_3 = stocks[:3]
                final_watchlist[sector] = [s.ticker.replace(".NS", "") for s in top_3]
                logger.info(
                    f"  🎯 {sector}: Selected top {len(final_watchlist[sector])} from {len(stocks)} eligible"
                )
            else:
                final_watchlist[sector] = []
                logger.info(f"  ❌ {sector}: No stocks passed validation")

        return final_watchlist


class EnhancedStockSelector(StockSelector):
    """
    Enhanced selector with dynamic sector discovery and flexible matching.
    """

    def select_stocks_with_mapping(self, sectors: List[str]) -> Dict[str, List[str]]:
        """
        Select stocks with flexible sector matching (no hardcoded mapping).
        Uses actual sector names from market data.
        """
        logger.info(f"📊 Selecting stocks for sectors: {sectors}")
        # Use flexible matching directly - no expansion needed
        return self.select_stocks(sectors)

    def get_top_sectors_from_market_and_select(
        self, top_n: int = 3
    ) -> Dict[str, List[str]]:
        """
        Discover top sectors from market and select stocks for them.
        This is the recommended method that uses actual market sectors.
        """
        # First, discover top sectors from market
        top_sectors = self.get_top_sectors_from_market(top_n=top_n)

        if not top_sectors:
            logger.error("❌ No sectors found in market")
            return {}

        logger.info(
            f"🎯 Selected top {len(top_sectors)} sectors: {', '.join(top_sectors)}"
        )

        # Then select stocks for these sectors
        return self.select_stocks(top_sectors)


if __name__ == "__main__":
    # Example usage
    top_sectors = ["Technology", "Financial Services", "Automobile"]

    print("🚀 Starting Stock Selection with nsepython...")
    selector = EnhancedStockSelector()
    watchlist = selector.select_stocks_with_mapping(top_sectors)

    print("\n" + "=" * 50)
    print("📈 FINAL WATCHLIST")
    print("=" * 50)

    if not watchlist or all(not stocks for stocks in watchlist.values()):
        print("❌ No stocks met the required criteria.")
        print("\n💡 Troubleshooting Tips:")
        print("  - Check if nsepython is installed: pip install nsepython")
        print("  - Try different sector names")
        print("  - Check your internet connection")
        print("  - The financial criteria might be too strict")
    else:
        total_stocks = sum(len(stocks) for stocks in watchlist.values())
        print(f"✅ Found {total_stocks} stocks across {len(watchlist)} sectors")
        print()

        for sector, stocks in watchlist.items():
            print(f"🏷️  Sector: {sector}")
            if stocks:
                for i, stock in enumerate(stocks, 1):
                    print(f"   {i}. {stock}")
            else:
                print("   ❌ No stocks found")
            print()

    print("=" * 50)
