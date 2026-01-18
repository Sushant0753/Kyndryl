from fastapi import APIRouter, UploadFile, File, HTTPException
from services.azure_storage_service import AzureStorageService
from services.mongodb_service import MongoDBService
from services.document_processor import DocumentProcessor
from services.rag_service import RAGService
from utils.file_handler import FileHandler
from models.db_models import DocumentMetadata
from schema.upload import UploadResponse
from lib.logger import logger
import uuid
from datetime import datetime

router = APIRouter(prefix="/upload", tags=["Document Upload"])


@router.post("/", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document for processing

    Flow:
    1. Validate file type, MIME type, and size
    2. Generate UUID document_id
    3. Upload to Azure Blob Storage
    4. Process PDF (extract, chunk, embed)
    5. Store embeddings in Qdrant
    6. Store metadata in MongoDB
    7. Return document_id and metadata
    """
    document_id = None
    blob_name = None

    try:
        # Initialize services
        file_handler = FileHandler()
        azure_storage = AzureStorageService()
        mongodb_service = MongoDBService()
        document_processor = DocumentProcessor()
        rag_service = RAGService()

        logger.info(f"Upload started: {file.filename}")

        # Step 1: Validate file
        file_content = await file_handler.validate_file(file)
        file_size = len(file_content)

        # Step 2: Generate document_id
        document_id = str(uuid.uuid4())

        # Step 3: Upload to Azure Blob Storage
        blob_name = f"{document_id}_{file.filename}"
        blob_url = await azure_storage.upload_blob(file_content, blob_name)

        logger.info(f"File uploaded to Azure: {blob_name}")

        # Step 4: Process PDF
        chunks_with_metadata, total_pages = document_processor.process_pdf(
            blob_content=file_content,
            document_id=document_id,
            filename=file.filename or "unknown.pdf"
        )

        logger.info(f"PDF processed: {total_pages} pages, {len(chunks_with_metadata)} chunks")

        # Step 5: Generate embeddings and store in Qdrant
        rag_service.store_document_embeddings(chunks_with_metadata)

        logger.info(f"Embeddings stored in Qdrant")

        # Step 6: Store metadata in MongoDB (optional - disable if MongoDB not available)
        try:
            metadata = DocumentMetadata(
                document_id=document_id,
                filename=file.filename or "unknown.pdf",
                blob_url=blob_url,
                blob_name=blob_name,
                file_size=file_size,
                total_pages=total_pages,
                total_chunks=len(chunks_with_metadata),
                upload_timestamp=datetime.utcnow(),
                status="completed"
            )

            success = await mongodb_service.store_document_metadata(metadata)

            if not success:
                logger.warning("Failed to store metadata in MongoDB, but processing completed")
        except Exception as mongo_error:
            logger.warning(f"MongoDB metadata storage skipped: {mongo_error}")

        logger.info(f"Document upload completed: {document_id}")

        # Step 7: Return response
        return UploadResponse(
            document_id=document_id,
            filename=file.filename or "unknown.pdf",
            total_chunks=len(chunks_with_metadata),
            total_pages=total_pages,
            status="processing_complete",
            message=f"Document processed successfully with {len(chunks_with_metadata)} chunks",
            timestamp=datetime.utcnow().isoformat()
        )

    except ValueError as e:
        # Validation error
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Processing error - cleanup
        logger.error(f"Upload failed: {e}", exc_info=True)

        # Cleanup: Delete blob if it was created
        if blob_name:
            try:
                azure_storage = AzureStorageService()
                await azure_storage.delete_blob(blob_name)
                logger.info(f"Cleaned up blob: {blob_name}")
            except:
                pass

        # Cleanup: Delete MongoDB metadata if it was created
        if document_id:
            try:
                mongodb_service = MongoDBService()
                await mongodb_service.delete_document_metadata(document_id)
                logger.info(f"Cleaned up MongoDB metadata: {document_id}")
            except:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )
