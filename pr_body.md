## Summary

This PR implements all the core features described in the README for the Sundown daily review assistant.

## Features Implemented

### 1. pgvector & Embeddings
- Added `embedding` column (Vector(1536)) to Entry, Extractions, WeeklySummary, MonthlySummary models
- Created migration for pgvector extension (must be installed on PostgreSQL server)

### 2. Background Job Worker (arq/Redis)
- `worker.py` with async job functions:
  - `process_entry`: Extracts structured data using Claude Sonnet
  - `generate_weekly_summary`: Generates weekly summaries from daily extractions
  - `generate_monthly_summary`: Generates monthly summaries from weekly summaries
  - `transcribe_audio`: Transcribes voice recordings using faster-whisper
  - `generate_follow_ups`: Creates 2-3 targeted follow-up questions

### 3. Voice Input & Transcription
- Audio upload endpoint (`POST /entries/upload_audio`)
- MinIO integration for audio storage
- faster-whisper local transcription with language detection
- Background job for async transcription

### 4. Streaming Follow-up Questions
- `POST /entries/{entry_id}/follow_up/stream` - SSE streaming with Claude Haiku
- `POST /entries/{entry_id}/follow_up` - Background job for generating questions
- `GET /entries/{entry_id}/follow_up/questions` - Retrieve generated questions
- `PATCH /entries/follow_up_questions/{question_id}` - Save answers

### 5. Weekly/Monthly Summaries
- Cron jobs: Weekly (Sunday 6 AM), Monthly (1st of month 6 AM)
- Hierarchical summarization: daily > weekly > monthly
- Uses Claude Sonnet for narrative summaries with mood/energy arcs

### 6. Semantic Search
- `GET /entries/search` with query, source filter (entries/extractions/weekly/monthly), limit
- pgvector cosine distance ordering (embedding generation TODO)

### 7. User Profile Document
- New `UserProfile` model with personality_summary, core_themes, typical_mood_range, common_wins, common_struggles, long_term_goals, primary_language, entry_count
- Embedding column for semantic search

### 8. Mobile-First Web UI
- `templates/index.html` - Single-page app with auth, entry creation, voice recording, follow-ups, history, search
- `static/style.css` - Dark theme, responsive, animations
- `static/app.js` - Vanilla JS app with MediaRecorder API, SSE streaming, toast notifications

## Database Migrations
Two new migrations:
- `c88c6c4a3fc0`: pgvector extension + embedding columns
- `f3b2a1c9d8e7`: UserProfile table

## Configuration
- Added `REDIS_HOST` and `REDIS_PORT` to settings
- Requires: PostgreSQL with pgvector, Redis, MinIO, Anthropic API key

## To Run
```bash
# Terminal 1: API server
uv run uvicorn sundown.main:app --reload

# Terminal 2: Background worker
uv run arq worker.WorkerSettings
```