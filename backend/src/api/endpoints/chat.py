from fastapi import APIRouter, HTTPException
from services.rag_service import RAGService
from services.elevenlabs_service import ElevenLabsService
from services.azure_storage_service import AzureStorageService
from utils.language_detector import LanguageDetector
from schema.chat import ChatRequest, ChatResponse
from lib.logger import logger
import uuid
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["Chat"])


async def generate_audio_response(text: str, include_audio: bool) -> str:
    """
    Generate audio response if requested

    Args:
        text: Text to convert to audio
        include_audio: Whether to generate audio

    Returns:
        str: Audio URL or None if not requested/failed
    """
    if not include_audio:
        return None

    try:
        # Initialize TTS service
        tts_service = ElevenLabsService()

        if not tts_service.is_available():
            logger.warning("ElevenLabs TTS service not available, skipping audio generation")
            return None

        # Generate audio
        audio_content = tts_service.text_to_speech(text)
        if not audio_content:
            logger.warning("TTS conversion failed, continuing without audio")
            return None

        # Store audio in Azure Blob Storage
        azure_storage = AzureStorageService()
        audio_filename = f"audio_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}.mp3"
        audio_url = await azure_storage.upload_audio_blob(audio_content, audio_filename)

        logger.info(f"Audio response generated successfully: {audio_url}")
        return audio_url

    except Exception as e:
        logger.warning(f"Audio generation failed, continuing without audio: {e}")
        return None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint supporting both RAG and general queries with multi-language support

    **Features:**
    - Automatic language detection
    - Response in the same language as the query
    - Supports Hindi, English, Bengali, Tamil, Telugu, Marathi, Gujarati, and more

    **Logic:**
    - If document_id provided: Use RAG pipeline (semantic search + context-aware LLM)
    - If document_id is None: Direct LLM query (general banking knowledge)
    - Language is automatically detected and response is translated

    **Supported Languages:**
    - Hindi (हिन्दी)
    - English
    - Bengali (বাংলা)
    - Tamil (தமிழ்)
    - Telugu (తెలుగు)
    - Marathi (मराठी)
    - Gujarati (ગુજરાતી)
    - Kannada (ಕನ್ನಡ)
    - Malayalam (മലയാളം)
    - Punjabi (ਪੰਜਾਬੀ)
    - Odia (ଓଡ଼ିଆ)
    - Assamese (অসমীয়া)

    Args:
        request: ChatRequest with query and optional document_id

    Returns:
        ChatResponse with AI-generated response in user's language
    """
    try:
        rag_service = RAGService()
        language_detector = LanguageDetector()

        logger.info(f"Chat request: query='{request.query[:50]}...', document_id={request.document_id}")

        if request.document_id:
            # RAG mode - query with document context
            logger.info(f"Using RAG mode with document_id={request.document_id}")

            response_text, detected_language = rag_service.query_with_rag(
                user_query=request.query,
                document_id=request.document_id
            )

            language_name = language_detector.get_language_name(detected_language)

            # Generate audio response if requested
            audio_url = await generate_audio_response(response_text, request.include_audio)

            return ChatResponse(
                response=response_text,
                mode="rag",
                detected_language=detected_language,
                language_name=language_name,
                document_id=request.document_id,
                chunks_used=30,  # We retrieve top 30 chunks
                audio_url=audio_url
            )

        else:
            # General mode - no RAG
            logger.info("Using general mode (no document context)")

            response_text, detected_language = rag_service.query_without_rag(request.query)

            language_name = language_detector.get_language_name(detected_language)

            # Generate audio response if requested
            audio_url = await generate_audio_response(response_text, request.include_audio)

            return ChatResponse(
                response=response_text,
                mode="general",
                detected_language=detected_language,
                language_name=language_name,
                document_id=None,
                chunks_used=None,
                audio_url=audio_url
            )

    except ValueError as e:
        # Validation or query error
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Processing error
        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )
