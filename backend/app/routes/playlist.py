from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from app.services.transcript_service import fetch_playlist_videos
from app.tasks.celery_tasks import process_video_task


playlist_bp = Blueprint("playlist_bp", __name__)


# Abdul Bari DAA playlist (from your provided link).
DEFAULT_PLAYLIST_ID = "PLDN4rrl48XKpZkf03iYFl-O29szjTrs_O"


@playlist_bp.post("/ingest")
@jwt_required()
def ingest_playlist():
    payload = request.get_json(silent=True) or {}
    playlist_id = payload.get("playlist_id") or DEFAULT_PLAYLIST_ID

    try:
        videos = fetch_playlist_videos(playlist_id)
    except Exception as e:
        return jsonify({"message": f"Ingest failed: {str(e)}"}), 500

    videos_collection = current_app.config["MONGO_DB"]["videos"]

    inserted = 0
    for v in videos:
        existing = videos_collection.find_one({"video_id": v["video_id"]})
        if existing:
            # Retry processing for videos that are not processed yet.
            if not existing.get("processed", False):
                videos_collection.update_one(
                    {"video_id": v["video_id"]},
                    {"$set": {"processing_error": None}},
                )
                process_video_task.delay(v["video_id"])
            continue
        videos_collection.insert_one(
            {
                "video_id": v["video_id"],
                "title": v.get("title", "") or "",
                "playlist_id": playlist_id,
                "thumbnail_url": v.get("thumbnail_url", "") or "",
                "duration_seconds": v.get("duration_seconds", 0) or 0,
                "topics": v.get("topics", []) or [],
                "processed": False,
                "processing_error": None,
                "created_at": datetime.utcnow(),
            }
        )
        inserted += 1

        # Enqueue processing in background.
        process_video_task.delay(v["video_id"])

    return (
        jsonify(
            {
                "status": "processing",
                "video_count": inserted,
                "message": "Playlist ingest started. Video processing happens asynchronously.",
            }
        ),
        202,
    )


@playlist_bp.get("/videos")
@jwt_required()
def list_videos():
    videos_collection = current_app.config["MONGO_DB"]["videos"]
    # Only show videos from the default Abdul Bari playlist on the UI.
    # This prevents older/irrelevant videos (e.g., other instructors) from showing up.
    docs = list(
        videos_collection.find({"playlist_id": DEFAULT_PLAYLIST_ID}).sort("title", 1)
    )
    resp = []
    for d in docs:
        resp.append(
            {
                "video_id": d.get("video_id"),
                "title": d.get("title", ""),
                "thumbnail_url": d.get("thumbnail_url", ""),
                "processed": bool(d.get("processed", False)),
                "topics": d.get("topics", []) or [],
                "processing_error": d.get("processing_error"),
            }
        )
    return jsonify(resp), 200


# Test (Phase 3):
# 1) After starting Flask + Celery worker + MongoDB:
# curl -X POST http://localhost:5000/api/playlist/ingest \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer TOKEN_HERE" \
#   -d '{}'
# 2) Then:
# curl http://localhost:5000/api/playlist/videos \
#   -H "Authorization: Bearer TOKEN_HERE"

