# AlgoPath Workflow (File-to-File)

This document is meant to explain to your professors how the system moves from user actions to data/LLM processing across files.

## 1) Frontend: Authentication and Protected Routes

`frontend/src/context/AuthContext.jsx`
- Stores `token` and `user` in `localStorage`.
- On app load, decodes the JWT `exp` and auto-logs out when expired.
- Exposes `login(token, user)` and `logout()`.

`frontend/src/services/api.js`
- Creates an Axios client using `VITE_API_BASE_URL`.
- Automatically attaches `Authorization: Bearer <token>` on requests.
- On `401`, clears storage and redirects to `/`.

`frontend/src/pages/LoginPage.jsx` and `frontend/src/pages/RegisterPage.jsx`
- Call backend endpoints:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
- On success, call `AuthContext.login()` and navigate to `/dashboard`.

`frontend/src/App.jsx`
- Defines all routes.
- Implements `Protected` wrapper that redirects unauthenticated users to `/`.
- Wraps dashboard pages with `DashboardLayout` which renders:
  - `frontend/src/components/Sidebar.jsx`
  - the main content area.

`frontend/src/components/Sidebar.jsx`
- Shows navigation links using `NavLink`.
- Uses current `AuthContext.user` to render the avatar initials and name.
- Calls `logout()` when the user clicks `Logout`.

## 2) Backend: Flask App + Auth Endpoints

`backend/app/config.py`
- Loads environment variables from `backend/.env`.
- Exposes config constants used across the backend.

`backend/app/__init__.py`
- Creates the Flask app via `create_app()`.
- Enables CORS for `/api/*`.
- Initializes:
  - JWT via `flask_jwt_extended`
  - MongoDB access via `pymongo.MongoClient`
  - Flask-Limiter via Redis storage (falls back to in-memory if Redis is unavailable)
- Registers blueprints:
  - `backend/app/routes/auth.py` (implemented)
  - `backend/app/routes/playlist.py` (implemented)
  - `backend/app/routes/quiz.py` (implemented)
  - `backend/app/routes/recommendations.py` (implemented)
  - `backend/app/routes/progress.py` (implemented)
  - `backend/app/routes/leaderboard.py` (implemented)
  - `backend/app/routes/ai_tutor.py` (implemented)

`backend/app/routes/auth.py`
- Implements:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me` (protected)
- Uses `bcrypt` with 12 rounds to hash passwords.
- Returns JWT access tokens on register/login.

## 3) Upcoming Phases: How Data and LLM Tasks Should Flow

Even though the current commit has only the auth endpoints fully working, the remaining modules follow a clear pipeline:

### A) Playlist Ingestion Pipeline (Phase 3)

`backend/app/routes/playlist.py`
- `POST /api/playlist/ingest` receives a playlist id.
- Saves video metadata to MongoDB.
- Enqueues Celery tasks to process each video.

`backend/app/tasks/celery_tasks.py`
- `process_video_task(video_id)` is responsible for:
  - Fetching transcript (`transcript_service.fetch_transcript`)
  - Chunking into ~90-second units (`transcript_service.chunk_transcript`)
  - Generating questions (mock or Groq via `app/services/llm_provider.py`)
  - Creating embeddings locally (`embedding_service.get_embedding`)
  - Persisting transcripts + questions into MongoDB

`backend/app/services/transcript_service.py`
- `fetch_playlist_videos(playlist_id)` uses YouTube Data API v3.
- `fetch_transcript(video_id)` uses `youtube-transcript-api`.
- `chunk_transcript(...)` groups transcript items into ~90-second chunks and assigns a `topic_tag`.

### B) Quiz + Scoring Pipeline (Phase 4)

`backend/app/routes/quiz.py`
- `GET /api/quiz/questions/:video_id` returns question sets for the UI.
- `POST /api/quiz/submit`:
  - Loads the question from MongoDB
  - Computes semantic similarity using embeddings
  - Calls LLM examiner feedback (mock or Groq via `llm_provider`)
  - Produces final score + feedback
  - Stores quiz attempt history in `quiz_attempts`
- `POST /api/quiz/translate` translates `question_text` + `correct_answer` for multilingual UI.

`backend/app/services/evaluation_service.py`
- Contains the hybrid scoring logic (LLM score + embedding similarity).

`backend/app/services/recommendation_service.py`
- Reads quiz attempts.
- Detects weak topics by averaging `final_score` and picking lowest topics.

### C) Recommendations and Timestamp Redirects (Phase 5/6)

`backend/app/routes/recommendations.py`
- `GET /api/recommendations/:user_id` returns:
  - weak topic name
  - average score
  - recommended video id and exact timestamp

This is what drives:
- `frontend/src/pages/WeakTopicsPage.jsx` (radar + list)
- `frontend/src/pages/TimelinePage.jsx` (timestamp cards)

Additional analytics endpoints:
- `backend/app/routes/progress.py` powers `frontend/src/pages/ProgressPage.jsx`
- `backend/app/routes/leaderboard.py` powers `frontend/src/pages/LeaderboardPage.jsx`

### D) AI Tutor RAG (Phase 7)

`backend/app/routes/ai_tutor.py`
- `POST /api/ai_tutor/chat`:
  - Embeds user query
  - Retrieves the top transcript chunks (RAG)
  - Calls Groq with system + context chunks
  - Returns the answer plus the context chunks used

`backend/app/services/embedding_service.py`
- Runs sentence-transformers locally.
- Performs cosine similarity to find relevant chunks.

`backend/app/services/llm_service.py`
- All LLM calls use the Groq SDK and `llama-3.3-70b-versatile`.
- Includes translation (`en`/`hi`/`ta`/`te`) and tutor response generation.

## 4) Where to Look for “Exactly What Happens”

If you want to explain the runtime path, these are the best “story lines”:

Login path:
1. `frontend/src/pages/LoginPage.jsx` -> `POST /api/auth/login`
2. `backend/app/routes/auth.py` verifies bcrypt hash and returns JWT
3. `frontend/src/context/AuthContext.jsx` saves token and user
4. `frontend/src/App.jsx` allows dashboard routes

Quiz path (implemented):
1. `frontend/src/pages/QuizPage.jsx` -> `GET /api/quiz/questions/:video_id`
2. `frontend/src/pages/QuizPage.jsx` -> `POST /api/quiz/submit`
3. `backend/app/routes/quiz.py` computes semantic + LLM evaluation
4. `backend/app/services/recommendation_service.py` refreshes weak topics
5. `frontend/src/pages/WeakTopicsPage.jsx` and `TimelinePage.jsx` use returned timestamps

