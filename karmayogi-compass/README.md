# Karmayogi Compass — Backend (SIH26101)

AI-powered skill intelligence layer for India's Official Statistical System (MoSPI), built on
top of iGOT Karmayogi. FastAPI + SQLModel + an adapter-pattern iGOT client + a RAG/LLM quiz engine.

## Quick start

```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then fill in GEMINI_API_KEY
python run.py                                         # serves on http://localhost:8000
```

Interactive docs: `http://localhost:8000/docs`

Two demo users are auto-seeded on first run (password for both: `Karmayogi@123`):
- `aditi.sharma@mospi.gov.in` — role `official`, designation "Statistical Officer"
- `ravi.kumar@mospi.gov.in` — role `admin`, designation "Director"

## Architecture

```
app/
  models/       SQLModel tables: User, CompetencyProfile, Course, Assessment, CompetencyPassport
  schemas/      Pydantic v2 request/response contracts
  adapters/     IGOTAdapter (ABC) + MockIGOTAdapter + LiveIGOTAdapter + factory switch
  services/     business logic — auth, skill-gap math, recommendations, RAG, LLM client,
                quiz generation, passport/scoring
  api/v1/       route handlers, one file per resource
  main.py       app factory, CORS, startup seeding
```

**iGOT Adapter pattern**: every course lookup goes through `app/adapters/base.py`'s
`IGOTAdapter` interface. `MockIGOTAdapter` serves bundled fixtures; `LiveIGOTAdapter` calls
real iGOT HTTP endpoints. Flip `IGOT_MODE=mock` ↔ `live` in `.env` — no other code changes.

**RAG quiz pipeline** (`app/services/rag_service.py`, `quiz_service.py`):
1. Uploaded PDF is split into overlapping word-window chunks, each tagged with its source page.
2. Chunks are embedded locally with a TF‑IDF vectorizer (no external model download — fully
   offline and deterministic) and stored in an ephemeral in-memory ChromaDB collection.
3. Questions are allocated across the four competency domains proportional to the user's
   current skill-gap size (`compute_domain_weighting`), always summing to 10.
4. For each domain, the top-matching chunks are retrieved and passed to the LLM (via LiteLLM,
   via Gemini) with a strict system prompt enforcing MoSPI workplace
   scenarios, 4-option strict-JSON output, and a source page citation per question.
5. Correct answers/explanations are stored server-side on the `Assessment` row and stripped
   before the quiz is returned to the client.

**Scoring** (`passport_service.py`): on submit, per-domain accuracy boosts that domain's
`CompetencyProfile` score (capped per assessment), gaps are recomputed, and the
`CompetencyPassport.overall_readiness_index` is refreshed as the mean of all four scores.
Domains scored ≥70% accuracy are appended to `validated_skills`.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/auth/login` | returns a JWT bearer token |
| GET  | `/api/v1/profile/me` | current user's profile + scores |
| GET  | `/api/v1/skillgap/{user_id}` | Required − Current per domain, sorted by gap |
| GET  | `/api/v1/recommendations/{user_id}` | iGOT courses weighted toward the biggest gaps |
| POST | `/api/v1/quiz/generate` | multipart: `user_id` + PDF `file` → 10-question gap-weighted quiz |
| POST | `/api/v1/quiz/submit` | `{assessment_id, user_id, answers[]}` → score + profile/passport update |
| GET  | `/api/v1/analytics/dashboard` | user view for officials, aggregate view for admins |

All endpoints except `/auth/login` require `Authorization: Bearer <token>`. Non-admin users can
only access their own `user_id` on skill-gap/recommendations/quiz endpoints (403 otherwise).

## Configuration (`.env`)

| Var | Purpose |
|---|---|
| `IGOT_MODE` | `mock` (bundled fixtures) or `live` (real iGOT HTTP endpoints) |
| `IGOT_BASE_URL`, `IGOT_API_KEY` | used only when `IGOT_MODE=live` |
| `LLM_MODEL` | LiteLLM model string, e.g. `gemini/gemini-1.5-flash` |
| `GEMINI_API_KEY` | your Gemini API key |
| `SECRET_KEY` | JWT signing secret — change for anything beyond local demo |

## Notes / known limitations

- SQLite is used for simplicity; swap `DATABASE_URL` for Postgres in production (SQLModel/SQLAlchemy
  handles the dialect change with no model code changes).
- `quiz/generate` requires a working `GEMINI_API_KEY` — everything else (auth,
  profile, skill-gap, recommendations, analytics) has been tested end-to-end with no external
  dependencies. The quiz pipeline itself (PDF→RAG→prompt building→storage→grading) has been
  verified with the LLM call mocked.
- Auth is JWT + bcrypt; there's no refresh-token flow or password reset — add if taking this to
  production.
