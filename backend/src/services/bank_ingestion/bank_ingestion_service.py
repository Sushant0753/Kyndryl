"""
BankIngestionService orchestrates the full SBI data ingestion pipeline:
1. Run all data sources (web scraper, PDF downloader, RSS news)
2. Deduplicate via SHA256 content hash stored in MongoDB
3. Chunk text using existing TextChunker
4. Generate embeddings using existing EmbeddingService
5. Store in Qdrant SBI_BANK_DATA collection
6. Log run metadata to MongoDB bank_ingestion_logs collection
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from configs.config import DocumentDB, SBIIngestionSettings
from services.bank_ingestion.sbi_web_scraper import SBIWebScraper
from services.bank_ingestion.sbi_pdf_downloader import SBIPDFDownloader
from services.bank_ingestion.sbi_news_rss_service import SBINewsRSSService
from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService
from utils.text_processor import TextChunker
from lib.logger import logger


class BankIngestionService:
    def __init__(self):
        self.settings = SBIIngestionSettings()
        self.db_settings = DocumentDB()
        self.mongo_client = AsyncIOMotorClient(self.db_settings.DOCUMENT_DB_CONNECTION_STRING)
        self.db = self.mongo_client[self.db_settings.DATABASE_NAME]
        self.logs_collection = self.db["bank_ingestion_logs"]
        self.hashes_collection = self.db["bank_ingestion_hashes"]
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()
        self.text_chunker = TextChunker()
        self.collection_name = self.settings.SBI_COLLECTION_NAME  # "SBI_BANK_DATA"
        # Ensure SBI_BANK_DATA collection exists in Qdrant on startup
        self.qdrant_service.ensure_collection(self.collection_name)
        logger.info("BankIngestionService initialized")

    async def run_full_ingestion(self) -> Dict:
        """
        Run the full ingestion pipeline. Called by APScheduler daily.
        Returns summary dict with run stats.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        logger.info(f"Starting bank ingestion run: {run_id}")

        new_chunks_stored = 0
        skipped_duplicates = 0
        sources_processed = 0
        errors = []

        try:
            # 1. Collect raw data from all sources
            raw_items = []

            try:
                with SBIWebScraper() as scraper:
                    web_items = scraper.scrape_pages()
                    press_items = scraper.scrape_press_releases()
                    raw_items.extend(web_items)
                    raw_items.extend(press_items)
                    logger.info(f"Web scraper collected {len(web_items) + len(press_items)} items")
            except Exception as e:
                errors.append(f"Web scraper error: {str(e)}")
                logger.error(f"Web scraper failed: {e}", exc_info=True)

            try:
                with SBIPDFDownloader() as downloader:
                    pdf_items = downloader.download_and_extract()
                    raw_items.extend(pdf_items)
                    logger.info(f"PDF downloader collected {len(pdf_items)} items")
            except Exception as e:
                errors.append(f"PDF downloader error: {str(e)}")
                logger.error(f"PDF downloader failed: {e}", exc_info=True)

            try:
                news_service = SBINewsRSSService()
                news_items = news_service.fetch_news()
                raw_items.extend(news_items)
                logger.info(f"RSS service collected {len(news_items)} items")
            except Exception as e:
                errors.append(f"RSS service error: {str(e)}")
                logger.error(f"RSS service failed: {e}", exc_info=True)

            sources_processed = len(raw_items)
            logger.info(f"Total raw items collected: {sources_processed}")

            # 2. Process each item: deduplicate, chunk, embed, store
            for item in raw_items:
                try:
                    text = item.get('text', '').strip()
                    if not text:
                        continue

                    content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

                    # Check if already ingested
                    existing = await self.hashes_collection.find_one({"hash": content_hash})
                    if existing:
                        skipped_duplicates += 1
                        continue

                    # Chunk the text
                    chunks = self.text_chunker.chunk_text(text, enhanced=True)
                    if not chunks:
                        continue

                    # Generate embeddings
                    embeddings = self.embedding_service.generate_embeddings(chunks)

                    # Build Qdrant payload for each chunk
                    ingestion_date = datetime.now(timezone.utc).isoformat()
                    chunks_with_payload = []
                    for idx, (chunk_text, _) in enumerate(zip(chunks, embeddings)):
                        chunks_with_payload.append({
                            "text": chunk_text,
                            "source_type": item.get("source_type", "unknown"),
                            "source_url": item.get("url", ""),
                            "source_title": item.get("title", ""),
                            "content_hash": content_hash,
                            "ingestion_date": ingestion_date,
                            "bank": "SBI",
                            "chunk_index": idx,
                            "total_chunks": len(chunks),
                            # Include dummy fields QdrantService expects
                            "document_id": content_hash,
                            "filename": item.get("title", "SBI Document"),
                            "page_number": 0,
                            "timestamp": ingestion_date,
                        })

                    # Store in Qdrant SBI_BANK_DATA
                    self.qdrant_service.store_chunks(
                        chunks_with_payload, embeddings, collection_name=self.collection_name
                    )
                    new_chunks_stored += len(chunks)

                    # Mark hash as ingested
                    await self.hashes_collection.insert_one({
                        "hash": content_hash,
                        "source_url": item.get("url", ""),
                        "ingested_at": datetime.now(timezone.utc).isoformat()
                    })

                except Exception as e:
                    errors.append(f"Item processing error ({item.get('url', 'unknown')}): {str(e)}")
                    logger.error(f"Failed to process item: {e}", exc_info=True)

            # 3. Log the run
            status = "success" if not errors else ("partial" if new_chunks_stored > 0 else "failed")
            completed_at = datetime.now(timezone.utc)

            run_log = {
                "run_id": run_id,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "status": status,
                "sources_processed": sources_processed,
                "new_chunks_stored": new_chunks_stored,
                "skipped_duplicates": skipped_duplicates,
                "errors": errors
            }
            await self.logs_collection.insert_one(run_log)

            logger.info(
                f"Ingestion run {run_id} completed: "
                f"status={status}, new_chunks={new_chunks_stored}, "
                f"skipped={skipped_duplicates}, errors={len(errors)}"
            )
            return run_log

        except Exception as e:
            logger.error(f"Fatal error in ingestion run {run_id}: {e}", exc_info=True)
            raise

    async def get_last_run_status(self) -> Optional[Dict]:
        """Get the most recent ingestion run log."""
        try:
            doc = await self.logs_collection.find_one(
                sort=[("started_at", -1)]
            )
            if doc:
                doc.pop("_id", None)
            return doc
        except Exception as e:
            logger.error(f"Failed to get last run status: {e}", exc_info=True)
            return None
