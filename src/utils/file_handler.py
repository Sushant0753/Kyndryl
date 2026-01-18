from fastapi import UploadFile
from configs.config import DocumentSettings
from lib.logger import logger


class FileHandler:
    """Utility for file validation"""

    def __init__(self):
        self.settings = DocumentSettings()

    async def validate_file(self, upload_file: UploadFile) -> bytes:
        """
        Validate uploaded file for type, MIME type, and size

        Args:
            upload_file: FastAPI UploadFile object

        Returns:
            bytes: File content if valid

        Raises:
            ValueError: If file is invalid
        """
        # Read file content
        contents = await upload_file.read()

        # Validate file size
        file_size = len(contents)
        if file_size > self.settings.MAX_FILE_SIZE:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum allowed size "
                f"({self.settings.MAX_FILE_SIZE} bytes = {self.settings.MAX_FILE_SIZE / (1024*1024):.1f} MB)"
            )

        # Validate file extension
        filename = upload_file.filename or ""
        file_extension = filename[filename.rfind('.'):] if '.' in filename else ""

        if file_extension.lower() not in self.settings.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{file_extension}' not allowed. "
                f"Allowed types: {', '.join(self.settings.ALLOWED_EXTENSIONS)}"
            )

        # Validate MIME type
        content_type = upload_file.content_type or ""
        valid_mime_types = ["application/pdf"]

        if content_type not in valid_mime_types:
            raise ValueError(
                f"Invalid MIME type '{content_type}'. Expected 'application/pdf'"
            )

        logger.info(
            f"File validation successful: {filename}, "
            f"Size={file_size} bytes, Type={content_type}"
        )

        return contents
