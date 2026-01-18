from azure.storage.blob import BlobServiceClient, ContentSettings
from configs.config import AzureStorageSettings
from lib.logger import logger
from typing import Optional


class AzureStorageService:
    """Service for Azure Blob Storage operations"""

    def __init__(self):
        self.settings = AzureStorageSettings()
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.settings.AZURE_STORAGE_CONNECTION_STRING
            )
            self.container_name = self.settings.AZURE_STORAGE_CONTAINER_NAME
            self._ensure_container_exists()
            logger.info(f"Azure Storage Service initialized: Container={self.container_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Storage Service: {e}", exc_info=True)
            raise

    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
            else:
                logger.info(f"Container already exists: {self.container_name}")
        except Exception as e:
            logger.error(f"Error checking/creating container: {e}", exc_info=True)
            raise

    async def upload_blob(self, file_content: bytes, blob_name: str) -> str:
        """
        Upload file to Azure Blob Storage

        Args:
            file_content: File content as bytes
            blob_name: Name for the blob (e.g., "{document_id}_{filename}.pdf")

        Returns:
            str: Blob URL
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            # Set content type for PDF
            content_settings = ContentSettings(content_type='application/pdf')

            # Upload the blob
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings=content_settings
            )

            blob_url = blob_client.url
            logger.info(f"Blob uploaded successfully: {blob_name}, URL={blob_url}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload blob {blob_name}: {e}", exc_info=True)
            raise

    async def get_blob_url(self, blob_name: str) -> Optional[str]:
        """
        Get blob URL

        Args:
            blob_name: Name of the blob

        Returns:
            str: Blob URL or None if not found
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            if blob_client.exists():
                return blob_client.url
            else:
                logger.warning(f"Blob not found: {blob_name}")
                return None

        except Exception as e:
            logger.error(f"Failed to get blob URL for {blob_name}: {e}", exc_info=True)
            return None

    async def download_blob(self, blob_name: str) -> Optional[bytes]:
        """
        Download blob content

        Args:
            blob_name: Name of the blob

        Returns:
            bytes: Blob content or None if not found
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            if blob_client.exists():
                download_stream = blob_client.download_blob()
                content = download_stream.readall()
                logger.info(f"Blob downloaded successfully: {blob_name}, Size={len(content)} bytes")
                return content
            else:
                logger.warning(f"Blob not found for download: {blob_name}")
                return None

        except Exception as e:
            logger.error(f"Failed to download blob {blob_name}: {e}", exc_info=True)
            return None

    async def delete_blob(self, blob_name: str) -> bool:
        """
        Delete blob from Azure Storage

        Args:
            blob_name: Name of the blob

        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            if blob_client.exists():
                blob_client.delete_blob()
                logger.info(f"Blob deleted successfully: {blob_name}")
                return True
            else:
                logger.warning(f"Blob not found for deletion: {blob_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}", exc_info=True)
            return False

    async def blob_exists(self, blob_name: str) -> bool:
        """
        Check if blob exists

        Args:
            blob_name: Name of the blob

        Returns:
            bool: True if exists, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            return blob_client.exists()

        except Exception as e:
            logger.error(f"Failed to check blob existence {blob_name}: {e}", exc_info=True)
            return False
