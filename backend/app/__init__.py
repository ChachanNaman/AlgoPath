from __future__ import annotations

import os
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
import certifi
import redis

from .config import Config


def _build_limiter() -> Limiter:
    """
    Build Flask-Limiter instance.

    Spec: initialize with Redis storage in dev; when Redis isn't available, fall back to in-memory
    so the app can still boot.
    """
    limiter_redis_url = Config.REDIS_URL or "redis://localhost:6379"
    try:
        redis_client = redis.Redis.from_url(limiter_redis_url)
        redis_client.ping()
        limiter_storage_uri = limiter_redis_url
    except Exception:
        limiter_storage_uri = None

    if limiter_storage_uri:
        return Limiter(
            key_func=get_remote_address,
            storage_uri=limiter_storage_uri,
        )
    return Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
    )


# Expose limiter for route decorators (e.g. limiter.limit(...)).
limiter = _build_limiter()


def _parse_db_name(mongo_uri: str) -> str:
    """
    Extract database name from a Mongo URI.
    Example: mongodb+srv://.../algopath?retryWrites=true -> algopath
    """
    try:
        parsed = urlparse(mongo_uri)
        path = (parsed.path or "").lstrip("/")
        return path.split("/")[0] if path else "algopath"
    except Exception:
        return "algopath"


def _append_mongo_query_param(uri: str, key: str, value: str) -> str:
    """Add query param to Mongo URI if missing."""
    if not uri:
        return uri
    parsed = urlparse(uri)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if key not in query:
        query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query)))


def _connect_mongo_database(mongo_uri: str, allow_invalid_tls: bool):
    """
    Connect to Mongo with resilient fallbacks:
    1) provided URI (Atlas/local)
    2) local mongodb://localhost:27017/algopath
    3) mongomock (in-memory) when enabled
    """
    primary_uri = mongo_uri
    if allow_invalid_tls:
        primary_uri = _append_mongo_query_param(primary_uri, "tlsAllowInvalidCertificates", "true")

    is_srv = primary_uri.startswith("mongodb+srv://")
    kwargs = {
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 10000,
        "socketTimeoutMS": 20000,
    }
    if is_srv:
        # Force CA bundle; helps on some macOS/network environments.
        kwargs["tlsCAFile"] = certifi.where()

    # Try primary URI first.
    client = MongoClient(primary_uri, **kwargs)
    db_name = _parse_db_name(primary_uri)
    db = client[db_name]
    db.command("ping")
    return db, "atlas-or-configured", primary_uri


def create_app() -> Flask:
    app = Flask(__name__)

    # Load config from env
    app.config.from_object(Config)
    app.config["JWT_SECRET_KEY"] = Config.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)

    # Dev friendly CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # JWT
    JWTManager(app)

    # Mongo
    # Development fallback:
    # If the user hasn't replaced placeholder values in `backend/.env`, use local MongoDB.
    mongo_uri = Config.MONGO_URI
    if not mongo_uri or "your_" in mongo_uri:
        mongo_uri = "mongodb://localhost:27017/algopath"

    mongo_db = None
    db_mode = "unknown"
    final_uri = mongo_uri
    try:
        mongo_db, db_mode, final_uri = _connect_mongo_database(
            mongo_uri, allow_invalid_tls=Config.MONGO_TLS_ALLOW_INVALID
        )
    except Exception:
        # Fallback to local MongoDB.
        try:
            local_uri = "mongodb://localhost:27017/algopath"
            mongo_db, db_mode, final_uri = _connect_mongo_database(local_uri, allow_invalid_tls=False)
            app.logger.warning("Primary MongoDB unavailable; falling back to local MongoDB.")
        except Exception:
            if not Config.USE_MOCK_DB:
                raise
            # Final fallback for demo reliability.
            import mongomock

            mock_client = mongomock.MongoClient()
            mongo_db = mock_client["algopath"]
            db_mode = "mongomock"
            final_uri = "mongomock://algopath"
            app.logger.warning("MongoDB unavailable; using in-memory mongomock fallback.")

    app.config["MONGO_DB"] = mongo_db
    app.config["DB_MODE"] = db_mode
    app.config["MONGO_EFFECTIVE_URI"] = final_uri

    limiter.init_app(app)

    # Register blueprints
    from .routes.auth import auth_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    # Stubs for other routes (added for import safety; real endpoints come in later phases)
    from .routes.playlist import playlist_bp
    from .routes.quiz import quiz_bp
    from .routes.evaluation import evaluation_bp
    from .routes.recommendations import recommendations_bp
    from .routes.ai_tutor import ai_tutor_bp
    from .routes.progress import progress_bp
    from .routes.leaderboard import leaderboard_bp

    app.register_blueprint(playlist_bp, url_prefix="/api/playlist")
    app.register_blueprint(quiz_bp, url_prefix="/api/quiz")
    app.register_blueprint(evaluation_bp, url_prefix="/api/evaluation")
    app.register_blueprint(recommendations_bp, url_prefix="/api/recommendations")
    app.register_blueprint(ai_tutor_bp, url_prefix="/api/ai_tutor")
    app.register_blueprint(progress_bp, url_prefix="/api/progress")
    app.register_blueprint(leaderboard_bp, url_prefix="/api/leaderboard")

    return app


# Expose app for `flask run` convenience
app = create_app()

