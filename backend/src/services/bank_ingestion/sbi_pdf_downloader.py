import time
from typing import List, Dict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from configs.config import SBIIngestionSettings
from lib.logger import logger
from services.ocr.pdf_processor import PDFProcessor


class SBIPDFDownloader:
    """Downloads and extracts text from publicly available SBI PDFs."""

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
        self.pdf_processor = PDFProcessor()
        logger.info("SBIPDFDownloader initialized")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def download_and_extract(self) -> List[Dict]:
        """
        Discover PDF links from each listing page, download each PDF, and
        extract its text via PyMuPDF.

        Returns:
            List of dicts with keys: title, text, url, source_type
        """
        results: List[Dict] = []

        for listing_path in self.settings.SBI_PDF_LISTING_URLS:
            listing_url = self.settings.SBI_BASE_URL + listing_path
            try:
                pdf_links = self._extract_pdf_links(listing_url)
                logger.info(
                    f"Found {len(pdf_links)} PDF link(s) on listing page: {listing_url}"
                )
            except Exception as exc:
                logger.error(
                    f"Failed to fetch PDF listing page {listing_url}: {exc}"
                )
                continue

            for pdf_url in pdf_links:
                try:
                    # Check size via HEAD request first
                    head = self.session.head(pdf_url, timeout=self.settings.SBI_REQUEST_TIMEOUT)
                    content_length = int(head.headers.get('content-length', 0))
                    max_pdf_bytes = 50 * 1024 * 1024  # 50 MB
                    if content_length > max_pdf_bytes:
                        logger.warning(f"Skipping PDF (too large: {content_length} bytes): {pdf_url}")
                        continue

                    response = self.session.get(pdf_url, timeout=self.timeout)
                    response.raise_for_status()

                    pdf_content = response.content
                    text = self.pdf_processor.extract_text_only(pdf_content)

                    if len(text) < 200:
                        logger.warning(
                            f"Skipping PDF with insufficient text ({len(text)} chars): {pdf_url}"
                        )
                        time.sleep(self.settings.SBI_REQUEST_DELAY)
                        continue

                    filename = pdf_url.rstrip("/").split("/")[-1]
                    results.append({
                        "title": filename,
                        "text": text,
                        "url": pdf_url,
                        "source_type": "pdf",
                    })
                    logger.info(
                        f"Extracted PDF: {filename} ({len(text)} chars)"
                    )
                except Exception as exc:
                    logger.error(f"Failed to download/extract PDF {pdf_url}: {exc}")

                time.sleep(self.settings.SBI_REQUEST_DELAY)

        return results

    def _extract_pdf_links(self, listing_url: str) -> List[str]:
        """
        Fetch a listing page and return absolute URLs for all .pdf links found,
        capped at SBI_MAX_PDFS_PER_RUN.

        Args:
            listing_url: Fully qualified URL of the page that lists PDFs.

        Returns:
            List of absolute PDF URLs.
        """
        response = self.session.get(listing_url, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        pdf_links: List[str] = []

        for anchor in soup.find_all("a", href=True):
            href: str = anchor["href"]
            if href.lower().endswith(".pdf"):
                absolute_url = urljoin(self.settings.SBI_BASE_URL, href)
                pdf_links.append(absolute_url)

                if len(pdf_links) >= self.settings.SBI_MAX_PDFS_PER_RUN:
                    break

        return pdf_links
