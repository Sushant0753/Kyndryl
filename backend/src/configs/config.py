import os
from typing import List
from pydantic_settings import BaseSettings

from services.credential_manager import get_secret

ENVIRONMENT = (os.getenv('ENVIRONMENT') or 'LOCAL').upper()

secret_keys_list = get_secret(ENVIRONMENT)

class AppInfo(BaseSettings):
    PROJECT_NAME: str = "Document Handling API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for vectorisation of given documents and chatting with them"
    API_STR: str = "/api"
    ALLOWED_ORIGINS: List[str] = ["*", "http://localhost:3000"]

class QdrantSettings(BaseSettings):
    QDRANT_HOST_URL:str=secret_keys_list['QDRANT_HOST_URL']
    QDRANT_API_KEY:str=secret_keys_list.get('QDRANT_API_KEY', '')
    QDRANT_COLLECTION_NAME:str='BANKING_RAG_DOCUMENTS'

class OllamaSettings(BaseSettings):
    OLLAMA_ENDPOINT_URL:str=secret_keys_list['OLLAMA_ENDPOINT_URL']

class DocumentDB(BaseSettings):
    DOCUMENT_DB_CONNECTION_STRING:str=secret_keys_list['DOCUMENT_DB_CONNECTION_STRING']
    DATABASE_NAME:str='banking_rag'
    COLLECTION_NAME:str='documents'

class AzureOpenAISettings(BaseSettings):
    # Embeddings endpoint
    AZURE_OPENAI_ENDPOINT:str=secret_keys_list['AZURE_OPENAI_ENDPOINT']
    AZURE_OPENAI_API_KEY:str=secret_keys_list['AZURE_OPENAI_API_KEY']
    AZURE_OPENAI_API_VERSION:str=secret_keys_list.get('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT:str="text-embedding-3-large"

    # Chat endpoint (can be different from embeddings)
    AZURE_OPENAI_CHAT_ENDPOINT:str=secret_keys_list.get('AZURE_OPENAI_CHAT_ENDPOINT', secret_keys_list['AZURE_OPENAI_ENDPOINT'])
    AZURE_OPENAI_CHAT_API_KEY:str=secret_keys_list.get('AZURE_OPENAI_CHAT_API_KEY', secret_keys_list['AZURE_OPENAI_API_KEY'])
    AZURE_OPENAI_CHAT_API_VERSION:str=secret_keys_list.get('AZURE_OPENAI_CHAT_API_VERSION', '2024-12-01-preview')
    AZURE_OPENAI_CHAT_DEPLOYMENT:str=secret_keys_list.get('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4o-2')

    EMBEDDING_DIMENSION:int=3072

class AzureStorageSettings(BaseSettings):
    AZURE_STORAGE_CONNECTION_STRING:str=secret_keys_list['AZURE_STORAGE_CONNECTION_STRING']
    AZURE_STORAGE_CONTAINER_NAME:str="banking-documents"

class DocumentSettings(BaseSettings):
    MAX_FILE_SIZE:int=10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS:List[str]=[".pdf"]
    CHUNK_SIZE:int=512
    CHUNK_OVERLAP:int=150

class BhashiniSettings(BaseSettings):
    # Bhashini API Configuration (for translation only)
    BHASHINI_USER_ID:str=secret_keys_list.get('BHASHINI_USER_ID', '')
    BHASHINI_API_KEY:str=secret_keys_list.get('BHASHINI_API_KEY', '')
    BHASHINI_PIPELINE_ID:str="64392f96daac500b55c543cd"
    BHASHINI_CONFIG_URL:str="https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

mongo_db_settings=DocumentDB()