import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = 604800  # 7 days in seconds
    # Development toggle: use mock LLM during early phases to avoid hitting Groq.
    # Set to False in Phase 7 when you are ready for real Groq calls.
    USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "True").lower() == "true"
    CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379")

