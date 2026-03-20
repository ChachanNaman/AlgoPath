# AlgoPath — Adaptive Learning System for DAA

## Architecture Workflow (File-to-File)

This app is split into a React frontend and a Flask backend. The backend orchestrates:
1. **Ingestion**: fetch YouTube playlist videos + extract transcripts + chunk transcripts into ~90s topic units.
2. **Question Generation**: send each chunk to an LLM (Groq) to generate 3 questions (easy/medium/hard).
3. **Embeddings + RAG**: generate local sentence-transformers embeddings for chunks/questions for fast semantic search.
4. **Quiz Evaluation**: for each submitted answer, score with (a) Groq examiner feedback and (b) embedding-based semantic similarity.
5. **Recommendations + Timeline**: identify weak topics from quiz history and map them back to exact transcript timestamps.
6. **AI Tutor Chat**: retrieve top matching transcript chunks (RAG) and answer grounded in the lecture context.

### Backend (what happens where)

`backend/app/__init__.py`
- Creates the Flask app instance.
- Enables CORS + JWT authentication + Flask-Limiter (Redis storage).
- Connects MongoDB (PyMongo-compatible access via a database handle in app config).
- Registers all route blueprints (auth/playlist/quiz/recommendations/ai_tutor).

`backend/app/config.py`
- Loads environment variables from `backend/.env`.
- Holds shared config for Groq, YouTube API, MongoDB, Redis, JWT, Celery.

`backend/app/routes/auth.py`
- Implements:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
- Uses bcrypt to hash passwords and returns JWT access tokens.

Phases will add:
- `backend/app/routes/playlist.py` (ingest playlist + enqueue Celery jobs)
- `backend/app/routes/quiz.py` (get questions + submit + compute final score)
- `backend/app/routes/recommendations.py` (weak topic recommendations)
- `backend/app/routes/ai_tutor.py` (RAG grounded tutor chat)

`backend/app/services/transcript_service.py`
- Uses YouTube APIs for playlist metadata and `youtube-transcript-api` for transcript text.
- Chunks transcripts into `~90s` units with `start_time`/`end_time`.

`backend/app/services/llm_service.py`
- Wraps **Groq SDK only** calls to:
  - generate exam questions
  - evaluate free-text answers
  - translate content
  - tutor responses

`backend/app/services/embedding_service.py`
- Runs sentence-transformers locally (`all-MiniLM-L6-v2`).
- Computes embeddings and cosine similarity for semantic scoring + RAG.

`backend/app/tasks/celery_tasks.py`
- Celery worker background pipeline:
  - fetch transcript -> chunk -> generate questions -> embed -> save to Mongo

### Frontend (what happens where)

`frontend/src/context/AuthContext.jsx`
- Stores JWT token in `localStorage`.
- Exposes `login`, `logout`, `user`, and `isAuthenticated`.

`frontend/src/services/api.js`
- Axios instance that attaches `Authorization: Bearer <token>` automatically.
- Clears session on `401` and redirects to `/`.

`frontend/src/App.jsx`
- Declares all routes:
  - `/` login
  - `/register`
  - `/dashboard/*` protected area (sidebar + pages)

`frontend/src/pages/*`
- Each page fetches its own data via backend routes and renders loading/error/empty states.

## Development Commands
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start services (in separate terminals)
redis-server                              # Terminal 1 (if using local Redis)
celery -A app.tasks.celery_tasks worker --loglevel=info   # Terminal 2
flask run --port=5000                     # Terminal 3

# Seed demo data
python seed.py

# Frontend setup
cd frontend
npm install
npm run dev     # Runs on http://localhost:5173
```

## Quick Auth Smoke Tests (Phase 1)

These verify register/login/me using curl.

1. Register:
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","password":"test123"}'
```

2. Login:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

3. Get me (replace `TOKEN_HERE`):
```bash
curl http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer TOKEN_HERE"
```

