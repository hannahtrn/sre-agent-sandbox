import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY: str   = os.getenv("OPENAI_API_KEY", "")
    CHROMA_HOST: str      = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int      = int(os.getenv("CHROMA_PORT", 8000))
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    GENERATION_MODEL: str  = "gpt-4o-mini"
    EMBEDDING_MODEL: str   = "text-embedding-3-small"
    RUNBOOK_COLLECTION: str = "sre_runbooks"

config = Config()
