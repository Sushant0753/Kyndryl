from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.speech_recognition_service import SpeechRecognitionService
from services.rag_service import RAGService
from services.elevenlabs_service import ElevenLabsService
from services.azure_storage_service import AzureStorageService
from utils.file_handler import FileHandler
from utils.language_detector import LanguageDetector
from schema.speech import TranscribeResponse, VoiceChatResponse
from lib.logger import logger
import uuid
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/speech", tags=["Speech"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form("en-US", description="Language code for transcription")
):
    """
    Transcribe audio file to text using Speech-to-Text

    **Supported Audio Formats:**
    - WAV, MP3, OGG, WebM, M4A, FLAC

    **Supported Languages:**
    - en-US (English - US)
    - hi-IN (Hindi)
    - bn-IN (Bengali)
    - ta-IN (Tamil)
    - te-IN (Telugu)
    - mr-IN (Marathi)
    - And more...

    **Flow:**
    1. Validate audio file format and size
    2. Convert to WAV if needed
    3. Transcribe using Google Speech Recognition with fallback to Sphinx
    4. Return transcribed text with confidence score

    Args:
        file: Audio file upload
        language: Target language for transcription (default: en-US)

    Returns:
        TranscribeResponse with transcribed text and metadata
    """
    try:
        # Initialize services
        file_handler = FileHandler()
        stt_service = SpeechRecognitionService()

        logger.info(f"STT request: {file.filename}, language={language}")

        # Step 1: Validate audio file
        audio_content, audio_format = await file_handler.validate_audio_file(file)

        # Step 2: Transcribe audio
        if language and language != "en-US":
            # Use language-specific transcription
            result = stt_service.transcribe_with_language(audio_content, language, audio_format)
        else:
            # Use default transcription
            result = stt_service.transcribe_audio(audio_content, audio_format)

        logger.info(f"STT completed: {len(result.get('text', ''))} characters transcribed")

        return TranscribeResponse(
            text=result.get('text', ''),
            confidence=result.get('confidence', 0.0),
            language=result.get('language', language or 'en-US'),
            engine=result.get('engine', 'unknown'),
            error=result.get('error')
        )

    except ValueError as e:
        # File validation error
        logger.error(f"Audio validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Processing error
        logger.error(f"Speech transcription failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Speech transcription failed: {str(e)}"
        )


@router.post("/voice-chat", response_model=VoiceChatResponse)
async def voice_chat(
    file: UploadFile = File(..., description="Audio file with user's voice message"),
    document_id: Optional[str] = Form(None, description="Document ID for RAG mode"),
    language: Optional[str] = Form("en-US", description="Language for speech recognition"),
    include_audio_response: Optional[bool] = Form(True, description="Include TTS audio response")
):
    """
    Complete voice chat pipeline: STT → Chat → TTS

    **Voice Chat Flow:**
    1. **Speech-to-Text**: Transcribe user's audio to text
    2. **Chat Processing**: Process transcribed text with AI (RAG or general mode)
    3. **Text-to-Speech**: Convert AI response back to audio (optional)

    **Features:**
    - Multi-language speech recognition
    - RAG mode with document context
    - Multi-language AI responses
    - Audio response generation
    - Error resilience with partial results

    Args:
        file: Audio file with user's voice message
        document_id: Optional document ID for RAG context
        language: Language for speech recognition
        include_audio_response: Whether to generate audio response

    Returns:
        VoiceChatResponse with transcription, chat response, and optional audio
    """
    errors = []
    transcribed_text = ""
    audio_url = None

    try:
        # Initialize services
        file_handler = FileHandler()
        stt_service = SpeechRecognitionService()
        rag_service = RAGService()
        language_detector = LanguageDetector()

        logger.info(f"Voice chat request: {file.filename}, document_id={document_id}, language={language}")

        # Step 1: Speech-to-Text
        try:
            audio_content, audio_format = await file_handler.validate_audio_file(file)

            if language and language != "en-US":
                stt_result = stt_service.transcribe_with_language(audio_content, language, audio_format)
            else:
                stt_result = stt_service.transcribe_audio(audio_content, audio_format)

            transcribed_text = stt_result.get('text', '')
            transcription_confidence = stt_result.get('confidence', 0.0)

            if not transcribed_text.strip():
                raise ValueError("No speech could be transcribed from the audio")

            logger.info(f"STT successful: '{transcribed_text[:50]}...', confidence={transcription_confidence}")

        except Exception as e:
            logger.error(f"STT failed: {e}")
            raise HTTPException(status_code=400, detail=f"Speech transcription failed: {str(e)}")

        # Step 2: Chat Processing
        try:
            if document_id:
                # RAG mode
                logger.info(f"Using RAG mode with document_id={document_id}")
                chat_response, detected_language = rag_service.query_with_rag(
                    user_query=transcribed_text,
                    document_id=document_id
                )
                mode = "rag"
                chunks_used = 30
            else:
                # General mode
                logger.info("Using general mode (no document context)")
                chat_response, detected_language = rag_service.query_without_rag(transcribed_text)
                mode = "general"
                chunks_used = None

            language_name = language_detector.get_language_name(detected_language)

            logger.info(f"Chat successful: {len(chat_response)} characters, language={detected_language}")

        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            errors.append(f"Chat processing failed: {str(e)}")
            chat_response = "I apologize, but I encountered an error processing your request."
            detected_language = "en"
            language_name = "English"
            mode = "error"
            chunks_used = None

        # Step 3: Text-to-Speech (optional)
        if include_audio_response and chat_response:
            try:
                tts_service = ElevenLabsService()

                if tts_service.is_available():
                    audio_content = tts_service.text_to_speech(chat_response)
                    if audio_content:
                        # Store audio in Azure Blob Storage
                        azure_storage = AzureStorageService()
                        audio_filename = f"voice_chat_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}.mp3"
                        audio_url = await azure_storage.upload_audio_blob(audio_content, audio_filename)
                        logger.info(f"TTS successful: {audio_url}")
                    else:
                        errors.append("TTS conversion failed")
                else:
                    errors.append("TTS service not available")

            except Exception as e:
                logger.warning(f"TTS failed, continuing without audio: {e}")
                errors.append(f"TTS failed: {str(e)}")

        logger.info(f"Voice chat completed: STT→Chat→TTS pipeline finished")

        return VoiceChatResponse(
            # STT results
            transcribed_text=transcribed_text,
            transcription_confidence=transcription_confidence,

            # Chat results
            chat_response=chat_response,
            mode=mode,
            detected_language=detected_language,
            language_name=language_name,
            document_id=document_id,
            chunks_used=chunks_used,

            # TTS results
            audio_url=audio_url,

            # Errors
            errors=errors if errors else None
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Catastrophic error
        logger.error(f"Voice chat failed catastrophically: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Voice chat processing failed: {str(e)}"
        )


@router.get("/supported-languages")
async def get_supported_languages():
    """
    Get list of supported languages for speech recognition

    Returns:
        dict: List of supported language codes and names
    """
    try:
        stt_service = SpeechRecognitionService()
        languages = stt_service.get_supported_languages()

        language_map = {
            "en-US": "English (US)",
            "en-GB": "English (UK)",
            "hi-IN": "Hindi (India)",
            "bn-IN": "Bengali (India)",
            "ta-IN": "Tamil (India)",
            "te-IN": "Telugu (India)",
            "mr-IN": "Marathi (India)",
            "gu-IN": "Gujarati (India)",
            "kn-IN": "Kannada (India)",
            "ml-IN": "Malayalam (India)",
            "pa-IN": "Punjabi (India)",
            "or-IN": "Odia (India)",
            "as-IN": "Assamese (India)",
            "en-IN": "English (India)"
        }

        supported = [
            {"code": lang, "name": language_map.get(lang, lang)}
            for lang in languages
        ]

        return {
            "supported_languages": supported,
            "total_count": len(supported)
        }

    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve supported languages")