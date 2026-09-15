# Karmayogi Compass — Backend (v0.9)

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

Three demo users are auto-seeded on first run (password for all three: `Karmayogi@123`):

| Email | Role | Designation | Department |
|---|---|---|---|
| `aditi.sharma@mospi.gov.in` | `official` | Statistical Officer | NSSO |
| `ravi.kishan@mospi.gov.in` | `admin` | Director | CSO |
| `priya.iyer@mospi.gov.in` | `official` | Junior Statistical Officer | FOD |

> **Renamed in v0.9:** the admin account was previously seeded as *Ravi Kumar* /
> `ravi.kumar@mospi.gov.in`. Existing local databases are migrated in place on the next
> startup — the account is renamed and re-pointed to the new address rather than duplicated,
> so the old row (and its history) is not left behind.

### Resetting a demo user

Once you've run a demo user through the full assessment flow, their scores, validated skills
and gap analysis stay on their account. To put one back to their seeded baseline:

```bash
python scripts/reset_user.py                            # defaults to Ravi Kishan
python scripts/reset_user.py priya.iyer@mospi.gov.in    # or name any seeded user
```

This deletes that user's assessment attempts, clears their passport's `validated_skills` and
their `identified_gaps`, and restores the domain scores from `app/adapters/mock_data.py`. The
account itself, its password and its role are untouched, so you can log straight back in and
run the flow from scratch.

## Architecture

```
app/
  models/       SQLModel tables: User, CompetencyProfile, Course, Assessment, CompetencyPassport
  schemas/      Pydantic v2 request/response contracts
  adapters/     IGOTAdapter (ABC) + MockIGOTAdapter + LiveIGOTAdapter + factory switch
  services/     business logic — auth, skill-gap math, recommendations, RAG, LLM client,
                quiz generation, passport/scoring
  api/v1/       route handlers, one file per resource
  templates/    server-rendered Jinja pages (dashboard, assessment, learning, passport, …)
  static/       vanilla JS + CSS for the front end — no build step
  main.py       app factory, CORS, startup seeding
scripts/
  reset_user.py utility to reset a seeded demo user back to baseline
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

**Compass AI** (`app/services/compass_ai_service.py`): the contextual assistant in the drawer on
the Learning page. It exposes two endpoints, both scoped by a `context` string the page passes in
(the course or module the learner currently has open):

* `POST /api/v1/compass-ai/suggestions` — three tappable starter questions for that module. If the
  LLM call fails, it degrades to generic module-aware chips rather than erroring out, so the UI
  always has something to show.
* `POST /api/v1/compass-ai/ask` — a short (under ~40 words) answer to the learner's question.
  `history` carries the running transcript as a flat alternating list (user, assistant, user, …)
  so follow-ups keep their referent; the last few turns are replayed to the model on each call,
  and the transcript is cleared whenever the page re-grounds the assistant on a new module.

Both calls route through the same LiteLLM/Gemini wrapper as the quiz pipeline, so there's only one
LLM integration to configure. With no `GEMINI_API_KEY` set, `/ask` returns an explicit
"not configured" message instead of inventing an answer.

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
| POST | `/api/v1/compass-ai/suggestions` | `{context}` → 3 quick-reply questions for the open module |
| POST | `/api/v1/compass-ai/ask` | `{context, question, history?}` → short contextual answer |

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
- `quiz/generate` and `compass-ai/ask` require a working `GEMINI_API_KEY` — everything else (auth,
  profile, skill-gap, recommendations, analytics) has been tested end-to-end with no external
  dependencies. `compass-ai/suggestions` still works without a key, falling back to generic chips. The quiz pipeline itself (PDF→RAG→prompt building→storage→grading) has been
  verified with the LLM call mocked.
- Auth is JWT + bcrypt; there's no refresh-token flow or password reset — add if taking this to
  production.
