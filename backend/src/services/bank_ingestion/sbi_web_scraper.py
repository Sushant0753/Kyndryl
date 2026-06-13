import time
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

from configs.config import SBIIngestionSettings
from lib.logger import logger


class SBIWebScraper:
    """Synchronous web scraper for SBI website pages."""

    def __init__(self):
        self.settings = SBIIngestionSettings()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        self.timeout = self.settings.SBI_REQUEST_TIMEOUT
        logger.info("SBIWebScraper initialized")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def scrape_pages(self) -> List[Dict]:
        """
        Scrape all configured SBI website pages.

        Returns:
            List of dicts with keys: title, text, url, source_type
        """
        results: List[Dict] = []
        for path in self.settings.SBI_SCRAPE_PAGES:
            url = self.settings.SBI_BASE_URL + path
            try:
                doc = self._scrape_page(url)
                results.append(doc)
                logger.info(f"Scraped page: {url} ({len(doc['text'])} chars)")
            except Exception as exc:
                logger.error(f"Failed to scrape page {url}: {exc}")
            time.sleep(self.settings.SBI_REQUEST_DELAY)
        return results

    def _scrape_page(self, url: str) -> Dict:
        """
        Scrape a single page and return a document dict.

        Args:
            url: Fully qualified URL to scrape.

        Returns:
            Dict with keys: title, text, url, source_type

        Raises:
            ValueError: If extracted text is shorter than 100 characters.
        """
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Remove noisy structural tags before text extraction
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "title"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        if len(text) < 100:
            raise ValueError(
                f"Extracted text too short ({len(text)} chars) for URL: {url}"
            )

        return {
            "title": title,
            "text": text,
            "url": url,
            "source_type": "website",
        }

    def scrape_press_releases(self) -> List[Dict]:
        """
        Scrape the SBI press releases page.

        Returns:
            List containing a single document dict for the press releases page.
        """
        url = self.settings.SBI_BASE_URL + self.settings.SBI_PRESS_RELEASE_URL
        results: List[Dict] = []
        try:
            doc = self._scrape_page(url)
            results.append(doc)
            logger.info(
                f"Scraped press releases page: {url} ({len(doc['text'])} chars)"
            )
            time.sleep(self.settings.SBI_REQUEST_DELAY)
        except Exception as exc:
            logger.error(f"Failed to scrape press releases page {url}: {exc}")
        return results
