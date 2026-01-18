from langchain_text_splitters import RecursiveCharacterTextSplitter
from configs.config import DocumentSettings
from typing import List
from lib.logger import logger


class TextChunker:
    """Utility for splitting text into chunks"""

    def __init__(self):
        self.settings = DocumentSettings()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.CHUNK_SIZE,  # 512
            chunk_overlap=self.settings.CHUNK_OVERLAP,  # 150
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        logger.info(
            f"TextChunker initialized: "
            f"chunk_size={self.settings.CHUNK_SIZE}, "
            f"chunk_overlap={self.settings.CHUNK_OVERLAP}"
        )

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks using recursive character splitter

        Args:
            text: Input text to be chunked

        Returns:
            List[str]: List of text chunks
        """
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided for chunking")
            return []

        chunks = self.splitter.split_text(text)
        logger.info(f"Text split into {len(chunks)} chunks")

        return chunks
