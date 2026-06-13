from typing import List, Dict

import feedparser
from bs4 import BeautifulSoup

from configs.config import SBIIngestionSettings
from lib.logger import logger

_MAX_ENTRIES_PER_FEED = 20
_MIN_TEXT_LENGTH = 50


class SBINewsRSSService:
    """Fetches SBI-related news articles via RSS feeds."""

    def __init__(self):
        self.settings = SBIIngestionSettings()
        logger.info("SBINewsRSSService initialized")

    def fetch_news(self) -> List[Dict]:
        """
        Parse each configured RSS feed and collect news entries.

        Returns:
            List of dicts with keys: title, text, url, source_type
        """
        results: List[Dict] = []

        for feed_url in self.settings.SBI_RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                if feed.bozo:
                    logger.error(f"RSS feed error for {feed_url}: {feed.bozo_exception}")
                entries_collected = 0

                for entry in feed.entries[:_MAX_ENTRIES_PER_FEED]:
                    title: str = entry.get("title", "Unknown")
                    raw_text: str = (
                        entry.get('summary', '')
                        or entry.get('description', '')
                        or (entry.get('content') or [{}])[0].get('value', '')
                    )
                    text = self._strip_html(raw_text)
                    url: str = entry.get("link", "")

                    if len(text) < _MIN_TEXT_LENGTH:
                        logger.debug(
                            f"Skipping RSS entry with short text ({len(text)} chars): {title}"
                        )
                        continue

                    results.append({
                        "title": title,
                        "text": text,
                        "url": url,
                        "source_type": "news",
                    })
                    entries_collected += 1

                logger.info(
                    f"Fetched {entries_collected} entries from RSS feed: {feed_url}"
                )
            except Exception as exc:
                logger.error(f"Failed to fetch RSS feed {feed_url}: {exc}")

        return results

    def _strip_html(self, html_text: str) -> str:
        """
        Strip HTML tags from text using BeautifulSoup.

        Args:
            html_text: Raw string that may contain HTML markup.

        Returns:
            Plain text with all HTML tags removed.
        """
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "lxml")
        return soup.get_text(separator=" ", strip=True)
