import time
from typing import List, Dict

import requests

from configs.config import SBIIngestionSettings
from lib.logger import logger

# Wikipedia's API policy requires a descriptive User-Agent identifying the application.
# Requests without one (or with the default "python-requests/x.x") get 403 Forbidden.
_WIKIPEDIA_USER_AGENT = (
    "SBIBankingRAG/1.0 (educational banking knowledge base; "
    "contact: banking-rag@example.com) python-requests"
)


class SBIWikipediaService:
    """
    Fetches full article text for SBI-related Wikipedia articles via the
    MediaWiki action=query API. No authentication required.
    """

    def __init__(self):
        self.settings = SBIIngestionSettings()
        logger.info("SBIWikipediaService initialized")

    def fetch_articles(self) -> List[Dict]:
        """
        Fetch each article in SBI_WIKIPEDIA_ARTICLES.
        Returns list of {title, text, url, source_type="wikipedia"} dicts.
        """
        results: List[Dict] = []
        headers = {"User-Agent": _WIKIPEDIA_USER_AGENT}
        for article_title in self.settings.SBI_WIKIPEDIA_ARTICLES:
            try:
                api_url = self.settings.SBI_WIKIPEDIA_API_URL.format(title=article_title)
                resp = requests.get(
                    api_url, headers=headers, timeout=self.settings.SBI_REQUEST_TIMEOUT
                )
                resp.raise_for_status()

                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                page = next(iter(pages.values()), {})

                if "missing" in page:
                    logger.warning(f"Wikipedia article not found: {article_title}")
                    continue

                extract = page.get("extract", "")
                if len(extract) < 200:
                    logger.warning(
                        f"Wikipedia article too short ({len(extract)} chars): {article_title}"
                    )
                    continue

                title = page.get("title", article_title)
                wiki_url = self._build_wiki_url(title)
                results.append({
                    "title": title,
                    "text": extract,
                    "url": wiki_url,
                    "source_type": "wikipedia",
                })
                logger.info(f"Fetched Wikipedia article: {title} ({len(extract)} chars)")

            except Exception as exc:
                logger.error(f"Failed to fetch Wikipedia article '{article_title}': {exc}")

            time.sleep(self.settings.SBI_REQUEST_DELAY)

        return results

    def _build_wiki_url(self, title: str) -> str:
        return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
