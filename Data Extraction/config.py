import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    # Optional: separate deployment for extraction (can be gpt-4o-mini, o1-mini, etc.)
    # If not set, falls back to AZURE_OPENAI_DEPLOYMENT_NAME
    AZURE_OPENAI_EXTRACTION_MODEL = os.getenv(
        "AZURE_OPENAI_EXTRACTION_MODEL",
        os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    )

    # Mini/lightweight model (for routing, classification, compaction)
    AZURE_OPENAI_MINI_DEPLOYMENT = os.getenv("AZURE_OPENAI_MINI_DEPLOYMENT", "gpt-4o-mini")

    # Batch extraction settings — tune to stay within your TPM quota
    EXTRACTION_BATCH_SIZE  = int(os.getenv("EXTRACTION_BATCH_SIZE", "8"))   # chunks per batch
    EXTRACTION_BATCH_SLEEP = int(os.getenv("EXTRACTION_BATCH_SLEEP", "3"))  # seconds between batches

    @classmethod
    def validate(cls):
        missing = []
        if not cls.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: missing.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        if not cls.AZURE_DOCUMENT_INTELLIGENCE_KEY: missing.append("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        if not cls.AZURE_OPENAI_ENDPOINT: missing.append("AZURE_OPENAI_ENDPOINT")
        if not cls.AZURE_OPENAI_KEY: missing.append("AZURE_OPENAI_API_KEY")
        
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
