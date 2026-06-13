import time
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from configs.config import SBIIngestionSettings
from lib.logger import logger

# Sections on sbi.bank.in that hold readable content
_CONTENT_SECTIONS = frozenset([
    "personal-banking", "corporate-banking", "home",
    "sbi-in-the-news", "media", "corporate-governance",
    "nri-services", "international-banking", "rural-banking",
    "digital-banking", "insurance", "investments",
])

# Path segments that indicate navigation/action pages rather than content
_SKIP_KEYWORDS = frozenset([
    "login", "logout", "register", "apply", "admin",
    "portal", "signedin", "signout", "callback",
])


class SBIWebScraper:
    """Synchronous web scraper for SBI website pages with dynamic link discovery."""

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

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scrape_pages(self) -> List[Dict]:
        """
        Discover and scrape SBI content pages.

        Starts from the configured seed pages, extracts internal links from
        each one, then scrapes every discovered content page up to 15 pages.
        """
        seed_urls = [self.settings.SBI_BASE_URL + p for p in self.settings.SBI_SCRAPE_PAGES]
        discovered = self._discover_content_pages(seed_urls)

        if not discovered:
            logger.warning("Link discovery returned nothing; will try seed pages directly")
            discovered = seed_urls

        results: List[Dict] = []
        for url in discovered:
            try:
                doc = self._scrape_page(url)
                results.append(doc)
                logger.info(f"Scraped page: {url} ({len(doc['text'])} chars)")
            except Exception as exc:
                logger.error(f"Failed to scrape page {url}: {exc}")
            time.sleep(self.settings.SBI_REQUEST_DELAY)

        return results

    def scrape_press_releases(self) -> List[Dict]:
        """Scrape the SBI press releases page."""
        url = self.settings.SBI_BASE_URL + self.settings.SBI_PRESS_RELEASE_URL
        results: List[Dict] = []
        try:
            doc = self._scrape_page(url)
            results.append(doc)
            logger.info(f"Scraped press releases page: {url} ({len(doc['text'])} chars)")
            time.sleep(self.settings.SBI_REQUEST_DELAY)
        except Exception as exc:
            logger.error(f"Failed to scrape press releases page {url}: {exc}")
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _discover_content_pages(self, seed_urls: List[str]) -> List[str]:
        """
        Fetch seed pages, extract internal /web/<section>/<page> links, and
        return up to 15 unique content page URLs. Seed pages that return 404
        are silently skipped — we only crawl from what actually responds.
        """
        discovered: Set[str] = set()
        base = self.settings.SBI_BASE_URL

        for seed in seed_urls:
            try:
                resp = self.session.get(seed, timeout=self.timeout)
                resp.raise_for_status()
                # Seed page itself counts as a valid content page
                discovered.add(resp.url)  # use final URL after any redirect

                soup = BeautifulSoup(resp.text, "lxml")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if not href:
                        continue
                    # Normalise relative → absolute
                    absolute = urljoin(base, href)
                    if self._is_content_url(absolute):
                        discovered.add(absolute)

                logger.info(
                    f"Discovered {len(discovered)} candidate pages after crawling {seed}"
                )
                time.sleep(self.settings.SBI_REQUEST_DELAY)

            except Exception as exc:
                logger.warning(f"Seed page unavailable, skipping: {seed} — {exc}")

        return list(discovered)[:15]

    def _is_content_url(self, url: str) -> bool:
        """Return True if url looks like a readable SBI content page."""
        try:
            parsed = urlparse(url)
            # Must be on the same host
            base_host = urlparse(self.settings.SBI_BASE_URL).netloc
            if parsed.netloc and parsed.netloc != base_host:
                return False
            # No query strings or fragments (those are usually modals / filters)
            if parsed.query or parsed.fragment:
                return False
            # Skip binary file extensions
            if any(parsed.path.lower().endswith(ext)
                   for ext in (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".xls", ".doc")):
                return False
            # Must be /web/<section>/<page> — at least 3 meaningful segments
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) < 3 or parts[0] != "web":
                return False
            # Section must be a known content area
            if parts[1] not in _CONTENT_SECTIONS:
                return False
            # Skip action/navigation pages
            last = parts[-1].lower()
            if any(kw in last for kw in _SKIP_KEYWORDS):
                return False
            return True
        except Exception:
            return False

    def _scrape_page(self, url: str) -> Dict:
        """
        Fetch and extract text from a single page.

        Raises:
            requests.HTTPError: on non-2xx response.
            ValueError: if extracted text is shorter than 100 characters.
        """
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

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
