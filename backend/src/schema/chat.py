from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """Request schema for chat endpoint"""
    query: str = Field(..., min_length=1, description="User's question")
    document_id: Optional[str] = Field(None, description="Optional document ID for RAG mode")
    include_audio: Optional[bool] = Field(False, description="Whether to include audio response (TTS)")


class ChatResponse(BaseModel):
    """Response schema for chat endpoint"""
    response: str = Field(..., description="AI-generated response")
    mode: str = Field(..., description="'rag' or 'general'")
    detected_language: str = Field(..., description="Detected language code (e.g., 'hi', 'en', 'bn')")
    language_name: str = Field(..., description="Full language name (e.g., 'Hindi', 'English')")
    document_id: Optional[str] = Field(None, description="Document ID used (if RAG mode)")
    chunks_used: Optional[int] = Field(None, description="Number of chunks retrieved (if RAG mode)")
    audio_url: Optional[str] = Field(None, description="URL to audio file (if TTS enabled)")
