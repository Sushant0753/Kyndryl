from fastapi import APIRouter, UploadFile, File, HTTPException
from services.azure_storage_service import AzureStorageService
from services.mongodb_service import MongoDBService
from services.document_processor import DocumentProcessor
from services.ocr_service import OCRService
from services.rag_service import RAGService
from utils.file_handler import FileHandler
from models.db_models import DocumentMetadata
from schema.upload import UploadResponse
from configs.config import DocumentSettings
from lib.logger import logger
import uuid
from datetime import datetime
import os

router = APIRouter(prefix="/upload", tags=["Document Upload"])


@router.post("/", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF or image) for processing

    Supported formats: PDF, JPG, JPEG, PNG

    Flow:
    1. Validate file type, MIME type, and size
    2. Generate UUID document_id
    3. Upload to Azure Blob Storage
    4. Process document:
       - PDF: Extract text, chunk, embed
       - Image: OCR text extraction, chunk, embed
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
        ocr_service = OCRService()
        rag_service = RAGService()
        doc_settings = DocumentSettings()

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

        # Step 4: Determine processing type and process document
        file_extension = os.path.splitext(file.filename or "")[1].lower()

        if file_extension in doc_settings.IMAGE_EXTENSIONS:
            # OCR processing path for images
            logger.info(f"Processing image file with OCR: {file.filename}")
            processing_type = "ocr"

            # Extract text using OCR
            extracted_text = ocr_service.extract_text_from_image(file_content)

            if not extracted_text.strip():
                raise ValueError("No text could be extracted from the image")

            # Create chunks from OCR text using document processor pattern
            chunks_with_metadata = document_processor.process_ocr_text(
                extracted_text=extracted_text,
                document_id=document_id,
                filename=file.filename or "unknown_image"
            )

            total_pages = 1  # Images are considered single page

            logger.info(f"OCR processed: {len(extracted_text)} characters extracted, {len(chunks_with_metadata)} chunks")

        else:
            # PDF processing path (existing logic)
            logger.info(f"Processing PDF file: {file.filename}")
            processing_type = "pdf"

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
            filename=file.filename or ("unknown_image" if processing_type == "ocr" else "unknown.pdf"),
            total_chunks=len(chunks_with_metadata),
            total_pages=total_pages,
            status="processing_complete",
            message=f"Document processed successfully with {len(chunks_with_metadata)} chunks using {processing_type.upper()} processing",
            timestamp=datetime.utcnow().isoformat(),
            processing_type=processing_type
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
