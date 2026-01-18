import fitz  # PyMuPDF
from utils.text_processor import TextChunker
from typing import List, Dict
from datetime import datetime
from lib.logger import logger
import io


class DocumentProcessor:
    """Service for processing PDF documents"""

    def __init__(self):
        self.text_chunker = TextChunker()
        logger.info("Document Processor initialized")

    def process_pdf(self, blob_content: bytes, document_id: str, filename: str) -> tuple[List[Dict], int]:
        """
        Extract text from PDF and create chunks with metadata

        Args:
            blob_content: PDF file content as bytes
            document_id: UUID for the document
            filename: Original filename

        Returns:
            tuple: (List of chunk dictionaries with metadata, total_pages)
        """
        try:
            # Open PDF from memory
            pdf_document = fitz.open(stream=blob_content, filetype="pdf")
            total_pages = len(pdf_document)

            logger.info(f"Processing PDF: {filename}, Pages={total_pages}")

            # Extract text with page markers
            full_text_parts = []

            for page_num in range(total_pages):
                page = pdf_document[page_num]
                page_text = page.get_text()

                # Add page markers for context
                marked_text = (
                    f"\n--- PAGE {page_num + 1} STARTS ---\n"
                    f"{page_text}"
                    f"\n--- PAGE {page_num + 1} ENDS ---\n"
                )
                full_text_parts.append(marked_text)

            pdf_document.close()

            # Combine all text
            combined_text = "".join(full_text_parts)

            # Chunk the text
            chunks = self.text_chunker.chunk_text(combined_text)

            logger.info(f"Generated {len(chunks)} chunks from {total_pages} pages")

            # Add metadata to each chunk
            chunks_with_metadata = []
            timestamp = datetime.utcnow().isoformat()

            for idx, chunk in enumerate(chunks):
                chunk_data = {
                    'text': chunk,
                    'document_id': document_id,
                    'chunk_index': idx,
                    'total_chunks': len(chunks),
                    'filename': filename,
                    'page_number': self._extract_page_number(chunk),
                    'timestamp': timestamp
                }
                chunks_with_metadata.append(chunk_data)

            return chunks_with_metadata, total_pages

        except Exception as e:
            logger.error(f"Failed to process PDF {filename}: {e}", exc_info=True)
            raise

    def _extract_page_number(self, chunk: str) -> int:
        """
        Extract page number from chunk markers

        Args:
            chunk: Text chunk with page markers

        Returns:
            int: Page number (1-indexed), or 0 if not found
        """
        import re
        match = re.search(r'PAGE (\d+) STARTS', chunk)
        if match:
            return int(match.group(1))
        return 0

    def extract_text_only(self, blob_content: bytes) -> str:
        """
        Extract plain text from PDF without chunking

        Args:
            blob_content: PDF file content as bytes

        Returns:
            str: Extracted text
        """
        try:
            pdf_document = fitz.open(stream=blob_content, filetype="pdf")
            text_parts = []

            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                text_parts.append(page.get_text())

            pdf_document.close()

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}", exc_info=True)
            raise
