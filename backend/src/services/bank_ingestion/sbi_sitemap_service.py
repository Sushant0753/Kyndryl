import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from configs.config import SBIIngestionSettings
from lib.logger import logger

_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Lower number = scraped first when capped at SBI_SITEMAP_MAX_PAGES
_SECTION_PRIORITY = {
    "web/personal-banking": 0,
    "web/interest-rates": 1,
    "web/faq-s": 2,
    "web/nri": 3,
    "web/business": 4,
    "web/investor-relations": 5,
    "web/corporate-governance": 6,
    "web/wealth-management": 7,
    "web/yono": 8,
    "corporate": 9,
}


def _section_priority(url: str) -> int:
    path = urlparse(url).path.lstrip("/")
    for prefix, priority in _SECTION_PRIORITY.items():
        if path.startswith(prefix):
            return priority
    return 99


class SBISitemapService:
    """
    Discovers every real SBI page via robots.txt → sitemap, then scrapes them.
    No hardcoded URL paths — zero guessing.
    """

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
        logger.info("SBISitemapService initialized")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape_via_sitemap(self) -> List[Dict]:
        """Discover real SBI page URLs via sitemap, scrape up to SBI_SITEMAP_MAX_PAGES."""
        urls = self._fetch_all_urls()
        logger.info(f"Sitemap discovery found {len(urls)} URLs to scrape")

        results: List[Dict] = []
        for url in urls:
            try:
                doc = self._scrape_page(url)
                results.append(doc)
                logger.info(f"Scraped: {url} ({len(doc['text'])} chars)")
            except Exception as exc:
                logger.warning(f"Skipping {url}: {exc}")
            time.sleep(self.settings.SBI_REQUEST_DELAY)

        return results

    # ------------------------------------------------------------------
    # Sitemap discovery
    # ------------------------------------------------------------------

    def _get_sitemap_url_from_robots(self) -> Optional[str]:
        """Parse robots.txt and return the first Sitemap: URL found."""
        robots_url = self.settings.SBI_BASE_URL + "/robots.txt"
        try:
            resp = self.session.get(robots_url, timeout=self.timeout)
            resp.raise_for_status()
            for line in resp.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    return line.split(":", 1)[1].strip()
        except Exception as exc:
            logger.warning(f"Could not read robots.txt: {exc}")
        return None

    def _fetch_all_urls(self) -> List[str]:
        """
        Build the full list of SBI page URLs from the sitemap.

        Steps:
        1. Try robots.txt for sitemap URL
        2. Fall back to SBI_SITEMAP_FALLBACK_URLS
        3. Parse the sitemap XML (handles both urlset and sitemapindex)
        4. Filter to sbi.bank.in only
        5. Sort by section priority
        6. Cap at SBI_SITEMAP_MAX_PAGES
        """
        sitemap_url = self._get_sitemap_url_from_robots()
        candidate_sitemaps = []
        if sitemap_url:
            candidate_sitemaps.append(sitemap_url)
        candidate_sitemaps.extend(self.settings.SBI_SITEMAP_FALLBACK_URLS)

        collected: List[str] = []
        visited: set = set()

        for sm_url in candidate_sitemaps:
            if sm_url in visited:
                continue
            visited.add(sm_url)
            self._parse_sitemap(sm_url, collected, visited)
            if collected:
                break  # found pages, no need to try fallbacks

        base_host = urlparse(self.settings.SBI_BASE_URL).netloc
        filtered = [u for u in collected if urlparse(u).netloc == base_host]
        filtered.sort(key=_section_priority)
        return filtered[: self.settings.SBI_SITEMAP_MAX_PAGES]

    def _parse_sitemap(self, sitemap_url: str, collected: List[str], visited: set) -> None:
        """
        Recursively parse a sitemap URL.
        Handles <sitemapindex> (contains child sitemaps) and <urlset> (contains page URLs).
        """
        try:
            resp = self.session.get(sitemap_url, timeout=self.timeout)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            tag = root.tag.split("}")[-1]  # strip namespace prefix

            if tag == "sitemapindex":
                for loc_el in root.findall("sm:sitemap/sm:loc", _SITEMAP_NS):
                    child_url = loc_el.text and loc_el.text.strip()
                    if child_url and child_url not in visited:
                        visited.add(child_url)
                        self._parse_sitemap(child_url, collected, visited)

            elif tag == "urlset":
                for loc_el in root.findall("sm:url/sm:loc", _SITEMAP_NS):
                    url = loc_el.text and loc_el.text.strip()
                    if url:
                        collected.append(url)

        except Exception as exc:
            logger.warning(f"Could not parse sitemap {sitemap_url}: {exc}")

    # ------------------------------------------------------------------
    # Page scraping
    # ------------------------------------------------------------------

    def _scrape_page(self, url: str) -> Dict:
        """
        Fetch a page and extract clean text.

        Raises:
            requests.HTTPError: on non-2xx response.
            ValueError: if extracted text is shorter than 100 characters.
        """
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "SBI Page"

        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "title"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        if len(text) < 100:
            raise ValueError(f"Text too short ({len(text)} chars)")

        return {
            "title": title,
            "text": text,
            "url": url,
            "source_type": "website",
        }
