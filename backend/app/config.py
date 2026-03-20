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


def _sanitize_redis_url_for_celery(url: str) -> str:
    """
    Celery's Redis backend requires ssl_cert_reqs for `rediss://` URLs.
    If it's missing, append `ssl_cert_reqs=CERT_NONE` so the worker can start.
    """
    if not url:
        return "redis://localhost:6379"
    if url.startswith("rediss://") and "ssl_cert_reqs=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}ssl_cert_reqs=CERT_NONE"
    return url


_SANITIZED_REDIS_URL = _sanitize_redis_url_for_celery(Config.REDIS_URL)

# Keep these as class attributes expected by the rest of the app.
Config.CELERY_BROKER_URL = _SANITIZED_REDIS_URL
Config.CELERY_RESULT_BACKEND = _SANITIZED_REDIS_URL

