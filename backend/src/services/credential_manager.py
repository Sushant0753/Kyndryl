import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_secret(environment_name):
    if environment_name == 'LOCAL':
        print('> LOCAL Environment detected. Using environment variables...')
        secret_keys_list = {
            # Azure OpenAI - Embeddings
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY", ""),
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),

            # Azure OpenAI - Chat (can be different endpoint)
            "AZURE_OPENAI_CHAT_ENDPOINT": os.getenv("AZURE_OPENAI_CHAT_ENDPOINT", os.getenv("AZURE_OPENAI_GPT_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT", ""))),
            "AZURE_OPENAI_CHAT_API_KEY": os.getenv("AZURE_OPENAI_CHAT_API_KEY", os.getenv("AZURE_OPENAI_GPT_API_KEY", os.getenv("AZURE_OPENAI_API_KEY", ""))),
            "AZURE_OPENAI_CHAT_API_VERSION": os.getenv("AZURE_OPENAI_CHAT_API_VERSION", os.getenv("AZURE_OPENAI_GPT_API_VERSION", "2024-12-01-preview")),
            "AZURE_OPENAI_CHAT_DEPLOYMENT": os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT", "gpt-4o-2")),

            # Azure Storage
            "AZURE_STORAGE_CONNECTION_STRING": os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),

            # Qdrant
            "QDRANT_HOST_URL": os.getenv("QDRANT_HOST_URL", "http://192.168.10.50:6333"),
            "QDRANT_API_KEY": os.getenv("QDRANT_API_KEY", ""),

            # MongoDB
            "DOCUMENT_DB_CONNECTION_STRING": os.getenv("DOCUMENT_DB_CONNECTION_STRING", "mongodb://192.168.10.50:27017/"),

            # Ollama (optional)
            "OLLAMA_ENDPOINT_URL": os.getenv("OLLAMA_ENDPOINT_URL", "http://192.168.10.50:11434"),

            # Bhashini API (for translation)
            "BHASHINI_USER_ID": os.getenv("BHASHINI_USER_ID", ""),
            "BHASHINI_API_KEY": os.getenv("BHASHINI_API_KEY", ""),

            # Legacy
            "BUCKET_NAME": os.getenv("BUCKET_NAME", "autoflow-test"),
        }

        return secret_keys_list

    else:
        # Production: fetch secrets from AWS Secrets Manager or Azure Key Vault
        secret_keys_list = {}  # TODO: Implement secret fetching
        return secret_keys_list