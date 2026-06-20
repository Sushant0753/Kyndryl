# FLIQ — AI Banking Assistant for Indian Customers

FLIQ is an AI-powered banking assistant built for Indian customers. It answers banking questions in multiple Indian languages, lets users upload their financial documents (bank statements, PAN cards, loan agreements) and ask questions about them, and supports both text and voice interaction.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [Backend](#backend-setup)
  - [Frontend](#frontend-setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Supported Languages](#supported-languages)
- [Project Structure](#project-structure)

---

## Features

- **Multi-language support** — responds in Hindi (Devanagari), Hinglish (auto-detected), English, and 9 other Indian languages
- **Document RAG** — upload a PDF or image of a financial document and ask questions about it; answers are grounded strictly in the document
- **Banking knowledge base** — built-in SBI knowledge base (accounts, loans, UPI, NEFT, RTGS, KYC, etc.) for questions without a document
- **Scanned document OCR** — PyMuPDF + Tesseract extract text from scanned PDFs and image files (PAN cards, bank statements)
- **Voice input + output** — record audio questions; get spoken responses via ElevenLabs TTS or browser Speech Synthesis fallback
- **Sentiment-aware responses** — detects frustrated, confused, or satisfied tone and adjusts explanation depth accordingly
- **Scope enforcement** — declines to answer questions unrelated to Indian banking; rejects non-banking documents
- **Automatic SBI knowledge refresh** — APScheduler ingests fresh SBI website content, Wikipedia articles, RSS news, and PDFs nightly

---

## Architecture

```
User (Browser)
    │
    ▼
Next.js Frontend (Port 3000)
    ├── /api/chat         → proxy → FastAPI /api/chat
    ├── /api/upload       → proxy → FastAPI /api/upload
    ├── /api/voice-chat   → proxy → FastAPI /api/speech/voice-chat
    └── /api/synthesize   → proxy → FastAPI /api/speech/synthesize
    │
    ▼
FastAPI Backend (Port 7000)
    │
    ├── Chat Endpoint
    │     ├── document_id present → RAG pipeline
    │     │     ├── Detect language (Unicode + Hinglish keywords)
    │     │     ├── Generate query embedding (Azure text-embedding-3-large)
    │     │     ├── Semantic search in Qdrant (BANKING_RAG_DOCUMENTS, filtered by document_id)
    │     │     └── LLM generates response grounded in document chunks
    │     │
    │     └── no document_id → General banking pipeline
    │           ├── Detect language
    │           ├── Search SBI_BANK_DATA collection in Qdrant
    │           └── LLM generates response from SBI knowledge base
    │
    ├── Upload Endpoint
    │     ├── PDF with selectable text → PyPDF2 extraction → chunk → embed → Qdrant
    │     └── Scanned PDF / image → PyMuPDF render → Tesseract OCR → chunk → embed → Qdrant
    │
    └── Speech Endpoints
          ├── STT: SpeechRecognition (Google API) → transcribed text
          ├── Chat: same as above (RAG or general)
          └── TTS: ElevenLabs multilingual v2 → Azure Blob Storage URL
    │
    ▼
External Services
    ├── Azure OpenAI    — chat completions (GPT-4o) + embeddings (text-embedding-3-large)
    ├── Qdrant          — vector database (BANKING_RAG_DOCUMENTS + SBI_BANK_DATA collections)
    ├── Azure Blob      — document and audio file storage
    ├── MongoDB Atlas   — document metadata (optional; degraded gracefully)
    └── ElevenLabs      — text-to-speech (browser SpeechSynthesis fallback if unavailable)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.9, Pydantic v2, APScheduler |
| LLM | Azure OpenAI GPT-4o (chat), text-embedding-3-large (3072-dim embeddings) |
| Vector DB | Qdrant (self-hosted or Qdrant Cloud) |
| OCR | PyMuPDF (fitz), Tesseract OCR (eng+hin+ben+tam+tel) |
| PDF parsing | PyPDF2, PyMuPDF |
| STT | SpeechRecognition (Google Speech API) |
| TTS | ElevenLabs multilingual v2 / browser `speechSynthesis` fallback |
| Storage | Azure Blob Storage |
| Database | MongoDB Atlas (optional metadata store) |
| Translation | Bhashini (MeitY — configured but optional) |

---

## Prerequisites

- Python 3.9+
- Node.js 18+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on the server with Hindi and other Indian language data packs
- Qdrant instance (cloud or local Docker: `docker run -p 6333:6333 qdrant/qdrant`)
- Azure subscription with:
  - Azure OpenAI resource (GPT-4o deployment + text-embedding-3-large deployment)
  - Azure Blob Storage account
- ElevenLabs account (optional — browser TTS is the fallback)
- MongoDB Atlas cluster (optional)

---

## Setup

### Backend Setup

```bash
cd backend/src

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r ../../requirements.txt

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your credentials (see Environment Variables section)

# Start the server
uvicorn main:app --host 0.0.0.0 --port 7000 --reload
```

The API will be available at `http://localhost:7000`.  
Interactive docs: `http://localhost:7000/api/vectoriser/openapi.json`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy and fill in environment variables
cp .env.example .env
# Set NEXT_PUBLIC_BACKEND_URL=http://localhost:7000

# Start the development server
npm run dev
```

The app will be available at `http://localhost:3000`.

---

## Environment Variables

### Backend (`backend/src/.env`)

| Variable | Description | Required |
|---|---|---|
| `QDRANT_HOST_URL` | Qdrant server URL (e.g. `http://localhost:6333`) | Yes |
| `QDRANT_API_KEY` | Qdrant API key (leave blank for local) | No |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint for embeddings | Yes |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key for embeddings | Yes |
| `AZURE_OPENAI_CHAT_ENDPOINT` | Azure OpenAI endpoint for chat (can be same) | Yes |
| `AZURE_OPENAI_CHAT_API_KEY` | Azure OpenAI API key for chat | Yes |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Chat model deployment name (e.g. `gpt-4o-2`) | Yes |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob Storage connection string | Yes |
| `AZURE_CONTAINER_NAME` | Blob container for documents (default: `banking-documents`) | No |
| `DOCUMENT_DB_CONNECTION_STRING` | MongoDB Atlas connection string | No |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS | No |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice ID | No |
| `BHASHINI_USER_ID` | Bhashini (MeitY) user ID for translation | No |
| `BHASHINI_API_KEY` | Bhashini API key | No |

### Frontend (`frontend/.env`)

| Variable | Description | Required |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | Backend base URL (e.g. `http://192.168.10.50:7000`) | Yes |

---

## API Reference

### Chat

```
POST /api/chat
Content-Type: application/json

{
  "query": "SBI mein savings account kaise kholein?",
  "document_id": "optional-uuid-from-upload"
}
```

**Response:**
```json
{
  "response": "SBI में सेविंग्स अकाउंट खोलना बहुत आसान है...",
  "mode": "rag | general",
  "detected_language": "hi",
  "language_name": "Hindi",
  "document_id": "uuid | null",
  "chunks_used": 30,
  "sentiment": "neutral | frustrated | confused | satisfied",
  "sentiment_confidence": 0.87
}
```

### Upload Document

```
POST /api/upload/
Content-Type: multipart/form-data

file: <PDF, JPG, JPEG, or PNG>  (max 10 MB)
```

**Response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "pan_card.pdf",
  "total_chunks": 4,
  "total_pages": 1,
  "status": "processing_complete",
  "processing_type": "ocr | pdf",
  "message": "Document processed successfully with 4 chunks using Enhanced OCR processing"
}
```

### Voice Chat

```
POST /api/speech/voice-chat
Content-Type: multipart/form-data

file: <WebM/MP3/WAV audio>
document_id: optional-uuid
include_audio_response: true | false
```

**Response:**
```json
{
  "transcribed_text": "SBI mein account kaise kholein",
  "chat_response": "SBI में अकाउंट खोलने के लिए...",
  "mode": "rag | general",
  "detected_language": "hi",
  "audio_url": "https://storage.blob.core.windows.net/.../response.mp3",
  "document_id": null,
  "errors": null
}
```

### Text-to-Speech

```
POST /api/speech/synthesize
Content-Type: multipart/form-data

text: "Your banking question answer here"
language: en | hi | bn | ...
```

**Response:**
```json
{ "audio_url": "https://storage.blob.core.windows.net/..." }
```

### Health Check

```
GET /api/health-check
```

### SBI Knowledge Base Admin

```
POST /api/bank-admin/trigger-ingestion   — manually trigger SBI data refresh
GET  /api/bank-admin/ingestion-status    — get last ingestion status and stats
```

---

## How It Works

### Document Q&A (RAG mode)

1. User uploads a financial document (PDF or image)
2. Backend extracts text:
   - **Selectable PDF** — PyPDF2 direct extraction
   - **Scanned PDF / image** — PyMuPDF renders each page at 2× zoom → Tesseract OCR
3. Text is chunked (512-token chunks, 150 overlap) and embedded with `text-embedding-3-large`
4. Embeddings are stored in Qdrant (`BANKING_RAG_DOCUMENTS` collection) tagged with the `document_id`
5. When the user asks a question, the query is embedded and searched against only that document's chunks
6. The LLM generates a response grounded strictly in the retrieved chunks
7. Non-banking documents are rejected — the assistant will not reveal their content

### General Banking Q&A

1. User asks a banking question without uploading a document
2. Query is embedded and searched against the `SBI_BANK_DATA` Qdrant collection
3. LLM generates a response using retrieved SBI knowledge base context
4. Off-topic questions (science, technology, cooking, etc.) are declined politely

### Language Handling

1. Language is detected via Unicode script range analysis
2. Hinglish (Hindi words in Roman script like "main", "kaise", "kya") is detected via a keyword set and treated as Hindi
3. If the user writes in Hindi or Hinglish, the LLM responds entirely in Hindi Devanagari script
4. Bhashini translation (MeitY API) is used when available for other Indian languages

### Voice Pipeline

```
User audio → STT (Google Speech API) → transcribed text
→ Language detection → [RAG or general] LLM response
→ ElevenLabs TTS → Azure Blob → audio URL sent to browser
→ (fallback: browser speechSynthesis if ElevenLabs unavailable)
```

---

## Supported Languages

| Language | Code | Script |
|---|---|---|
| Hindi (+ Hinglish) | hi | Devanagari / Roman |
| English | en | Roman |
| Bengali | bn | Bengali |
| Tamil | ta | Tamil |
| Telugu | te | Telugu |
| Marathi | mr | Devanagari |
| Gujarati | gu | Gujarati |
| Kannada | kn | Kannada |
| Malayalam | ml | Malayalam |
| Punjabi | pa | Gurmukhi |
| Urdu | ur | Nastaliq |

---

## Project Structure

```
Kyndryl/
├── backend/
│   └── src/
│       ├── main.py                     # FastAPI app factory + CORS + lifespan
│       ├── scheduler.py                # APScheduler — nightly SBI data ingestion
│       ├── api/
│       │   ├── routes.py               # Router aggregator
│       │   └── endpoints/
│       │       ├── chat.py             # POST /api/chat
│       │       ├── upload.py           # POST /api/upload/
│       │       ├── speech.py           # /api/speech/* (STT, voice-chat, TTS)
│       │       ├── bank_admin.py       # /api/bank-admin/* (manual ingestion trigger)
│       │       └── endpoints.py        # Health check
│       ├── services/
│       │   ├── rag_service.py          # RAG pipeline orchestration
│       │   ├── llm_service.py          # Azure OpenAI chat completions
│       │   ├── embedding_service.py    # Azure OpenAI text-embedding-3-large
│       │   ├── qdrant_service.py       # Qdrant CRUD + semantic search
│       │   ├── azure_storage_service.py
│       │   ├── mongodb_service.py      # Optional metadata store
│       │   ├── speech_recognition_service.py
│       │   ├── elevenlabs_service.py   # TTS + markdown stripping
│       │   ├── sentiment_service.py    # Customer sentiment analysis
│       │   ├── bhashini_service.py     # MeitY translation API
│       │   ├── ocr/
│       │   │   ├── enhanced_ocr_service.py  # Main OCR orchestrator
│       │   │   ├── pdf_processor.py         # PyPDF2 text extraction
│       │   │   ├── image_processor.py       # Tesseract OCR
│       │   │   └── chunking_service.py      # Text chunking
│       │   └── bank_ingestion/
│       │       ├── bank_ingestion_service.py
│       │       ├── sbi_web_scraper.py
│       │       ├── sbi_pdf_downloader.py
│       │       ├── sbi_news_rss_service.py
│       │       ├── sbi_sitemap_service.py
│       │       └── sbi_wikipedia_service.py
│       ├── utils/
│       │   ├── language_detector.py    # Unicode + Hinglish keyword detection
│       │   ├── file_handler.py         # Upload validation
│       │   └── text_processor.py
│       └── configs/
│           └── config.py               # Pydantic settings (all env vars)
│
└── frontend/
    ├── app/
    │   ├── page.tsx                    # Home page (first message + file upload)
    │   ├── chat/[sessionId]/page.tsx   # Chat session page
    │   └── api/
    │       ├── chat/route.ts           # Proxy → /api/chat
    │       ├── upload/route.ts         # Proxy → /api/upload/
    │       ├── voice-chat/route.ts     # Proxy → /api/speech/voice-chat
    │       └── synthesize/route.ts     # Proxy → /api/speech/synthesize
    ├── components/
    │   ├── ChatInput.tsx               # Input bar (text, file, mic, TTS toggle)
    │   └── Sidebar.tsx
    ├── hooks/
    │   └── useChatMessage/index.ts     # Chat state, upload, TTS, voice logic
    ├── services/
    │   └── useChatService/index.ts     # API call wrappers
    └── types/
        └── chat.ts
```

---

## Notes

- **Qdrant collections**: `BANKING_RAG_DOCUMENTS` stores user-uploaded document chunks; `SBI_BANK_DATA` stores the SBI knowledge base. Both are created automatically on first startup.
- **MongoDB is optional**: If MongoDB Atlas is unreachable, document metadata storage is skipped gracefully and the system continues to operate via Qdrant.
- **ElevenLabs is optional**: If the API key is not configured or quota is exhausted, the frontend falls back to the browser's built-in `speechSynthesis` API automatically.
- **Tesseract is required for image/scanned-PDF processing**: Without it, only selectable-text PDFs can be uploaded.
- **Document scope**: The assistant only processes banking and finance documents. Research papers, technical manuals, or other non-banking uploads are rejected with a clear message.
- **Data privacy**: Document embeddings are stored per `document_id` and are never cross-queried across different users' documents (each query filters strictly by the requester's `document_id`).
