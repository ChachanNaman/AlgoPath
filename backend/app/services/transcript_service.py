from __future__ import annotations

import os
import re
from typing import Any

from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi


KNOWN_TOPICS = [
    "Sorting",
    "Graphs",
    "Dynamic Programming",
    "Greedy",
    "Divide & Conquer",
    "Trees",
    "Hashing",
    "Backtracking",
]

DEFAULT_LANGUAGE_CANDIDATES = ["en", "en-US", "en-GB"]


def _pick_topic_tag(text: str) -> str:
    text_lower = (text or "").lower()

    # Priority matches first; helps keep "Divide & Conquer" distinct.
    topic_aliases = {
        "Divide & Conquer": ["divide and conquer", "divide&conquer"],
        "Dynamic Programming": ["dynamic programming", "dp"],
        "Greedy": ["greedy"],
        "Sorting": ["sort", "sorting", "merge sort", "quick sort"],
        "Graphs": ["graph", "graphs"],
        "Trees": ["tree", "trees"],
        "Hashing": ["hash", "hashing"],
        "Backtracking": ["backtracking", "backtrack"],
    }

    for canonical, aliases in topic_aliases.items():
        for a in aliases:
            if a in text_lower:
                return canonical

    # Fallback heuristic: if a strong keyword appears, pick it.
    if "merge sort" in text_lower or "quicksort" in text_lower or "quick sort" in text_lower:
        return "Sorting"

    return "General"


def fetch_playlist_videos(playlist_id: str) -> list[dict]:
    """
    Use YouTube Data API v3 to fetch up to 50 videos per page from the playlist.
    Handles pagination with `nextPageToken`.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or "your_" in api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY (set in backend/.env).")

    youtube = build("youtube", "v3", developerKey=api_key)

    videos: list[dict[str, Any]] = []
    page_token = None
    while True:
        req = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        )
        resp = req.execute()
        for item in resp.get("items", []):
            snippet = item.get("snippet", {})
            resource_id = snippet.get("resourceId", {}) or {}
            video_id = resource_id.get("videoId")
            if not video_id:
                continue

            thumbnails = snippet.get("thumbnails", {}) or {}
            thumb = (
                thumbnails.get("medium", {}) or {}
            ).get("url") or (
                thumbnails.get("default", {}) or {}
            ).get("url") or ""

            videos.append(
                {
                    "video_id": video_id,
                    "title": snippet.get("title", "") or "",
                    "thumbnail_url": thumb,
                    # topics will be refined later; keep an initial guess.
                    "topics": [],
                    "processed": False,
                }
            )

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return videos


def fetch_transcript(video_id: str) -> list[dict]:
    """
    Extract transcript from YouTube video.
    Returns list of {text, start, duration}.
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=DEFAULT_LANGUAGE_CANDIDATES
        )
    except Exception:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

    items: list[dict[str, Any]] = []
    for item in transcript:
        text = item.get("text", "") or ""
        # Normalize whitespace to help chunk similarity and embeddings.
        text = re.sub(r"\s+", " ", text).strip()
        items.append(
            {
                "text": text,
                "start": float(item.get("start", 0.0)),
                "duration": float(item.get("duration", 0.0)),
            }
        )
    return items


def chunk_transcript(transcript_items: list[dict], chunk_duration: int = 90) -> list[dict]:
    """
    Group transcript items into chunks where total duration is ~`chunk_duration`.
    Each chunk contains:
      - text
      - start_time
      - end_time
      - topic_tag
      - chunk_index
    """
    chunks: list[dict] = []
    if not transcript_items:
        return chunks

    current_texts: list[str] = []
    current_start = float(transcript_items[0]["start"])
    current_end = current_start

    chunk_index = 0
    for idx, item in enumerate(transcript_items):
        start = float(item["start"])
        duration = float(item.get("duration", 0.0))
        end = start + duration

        # Initialize start when we begin a new chunk.
        if not current_texts:
            current_start = start
            current_end = end
        else:
            current_end = max(current_end, end)

        current_texts.append(item.get("text", ""))

        # When we reach target duration, close the chunk.
        if (current_end - current_start) >= chunk_duration:
            text = re.sub(r"\s+", " ", " ".join(current_texts)).strip()
            chunks.append(
                {
                    "text": text,
                    "start_time": current_start,
                    "end_time": current_end,
                    "topic_tag": _pick_topic_tag(text),
                    "chunk_index": chunk_index,
                }
            )
            chunk_index += 1
            current_texts = []

    # Flush remaining items.
    if current_texts:
        text = re.sub(r"\s+", " ", " ".join(current_texts)).strip()
        chunks.append(
            {
                "text": text,
                "start_time": current_start,
                "end_time": current_end,
                "topic_tag": _pick_topic_tag(text),
                "chunk_index": chunk_index,
            }
        )

    return chunks


# Quick manual test (once implemented in Phase 3):
# - Call `fetch_playlist_videos(PLAYLIST_ID)` then `fetch_transcript(video_id)`
# - Pass transcript items to `chunk_transcript(...)`
# - Verify returned chunks contain: `text`, `start_time`, `end_time`, `topic_tag`, `chunk_index`

