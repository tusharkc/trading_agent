import os
from datetime import datetime, timedelta
from newsapi import NewsApiClient
from app.shared.config import config
from app.shared.logger import logger


class NewsFetcher:
    def __init__(self):
        self.newsapi = NewsApiClient(api_key=config.NEWS_API_KEY)

    def fetch_news(self, query, days=7):
        """
        Fetches news articles for a given query from the last 'days' days.
        """
        logger.info(f"📰 Fetching news for query: '{query}' for last {days} days...")

        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        try:
            all_articles = self.newsapi.get_everything(
                q=query, from_param=from_date, language="en", sort_by="relevancy"
            )

            articles = all_articles["articles"]
            logger.info(f"✅ Fetched {len(articles)} news articles for '{query}'.")
            return articles
        except Exception as e:
            logger.error(f"❌ Error fetching news for '{query}': {e}")
            return []
