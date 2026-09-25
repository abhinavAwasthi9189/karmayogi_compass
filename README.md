# Karmayogi Compass — Backend

AI-powered skill intelligence layer for India's Official Statistical System (MoSPI), built on
top of iGOT Karmayogi. FastAPI + SQLModel + an adapter-pattern iGOT client + a RAG/LLM quiz engine.

> **Data note:** this prototype runs on a seeded course corpus and mock iGOT dataset that mirror
> iGOT Karmayogi's real content structure. Live iGOT API access requires CBC/NPCSCB authorization,
> which we don't have during the hackathon window — see the `IGOT Adapter pattern` section below
> for how switching to the real API requires no application code changes.

## Quick start

```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then fill in GEMINI_API_KEY
python run.py                                         # serves on http://localhost:8000
```

Interactive docs: `http://localhost:8000/docs`

The app works fully with **no `GEMINI_API_KEY` set** — quiz generation and Compass AI both fall
back to pre-authored content. Add a working key to unlock AI-generated, corpus-grounded questions
and answers automatically; no other config changes needed.

Three demo users are auto-seeded on first run (password for all three: `Karmayogi@123`):

| Email | Role | Designation | Department |
|---|---|---|---|
| `aditi.sharma@mospi.gov.in` | `official` | Statistical Officer | NSSO |
| `ravi.kishan@mospi.gov.in` | `admin` | Director | CSO |
| `priya.iyer@mospi.gov.in` | `official` | Junior Statistical Officer | FOD |

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
models/ SQLModel tables: User, CompetencyProfile, Course, Assessment, CompetencyPassport
schemas/ Pydantic v2 request/response contracts
adapters/ IGOTAdapter (ABC) + MockIGOTAdapter + LiveIGOTAdapter + factory switch
services/ business logic — auth, skill-gap math, recommendations, RAG (corpus + PDF),
LLM client, quiz generation, passport/scoring, Compass AI
api/v1/ route handlers, one file per resource
templates/ server-rendered Jinja pages (dashboard, assessment, learning, passport, …)
static/ vanilla JS + CSS for the front end — no build step
main.py app factory, CORS, startup seeding
scripts/
reset_user.py utility to reset a seeded demo user back to baseline
```


**iGOT Adapter pattern**: every course lookup goes through `app/adapters/base.py`'s
`IGOTAdapter` interface. `MockIGOTAdapter` serves bundled fixtures; `LiveIGOTAdapter` calls
real iGOT HTTP endpoints. Flip `IGOT_MODE=mock` ↔ `live` in `.env` — no other code changes.

**Quiz generation** tries three sources, in order, so it never fails outright:

1. **Corpus-grounded RAG** (`app/services/corpus_rag.py` + `quiz_service.py`) — the default when
   a `GEMINI_API_KEY` is configured and no file is uploaded. Our own seeded course corpus
   (`mock/rag_learning_corpus_flat.csv`) is indexed locally with a TF-IDF vectorizer (plain
   scikit-learn + numpy — no external vector database, fully offline and deterministic). For each
   competency domain, the top-matching course modules are retrieved and passed to the LLM (via
   LiteLLM → Gemini) along with the learner's current score/gap for that domain, under a strict
   system prompt enforcing MoSPI workplace scenarios, 4-option strict-JSON output, and a
   `"Course — Module N"` citation per question.
2. **Uploaded-PDF RAG** (`app/services/rag_service.py`) — if a PDF is provided instead, it's
   chunked into overlapping word windows, TF-IDF indexed the same way, and cited by source page.
3. **Practice bank fallback** (`mock/practice_assessments.csv`) — used automatically whenever no
   key is configured, or the AI call fails for any reason (quota limit, transient provider outage,
   network error). This is intentional graceful degradation, not an error state — the terminal logs
   which source was used for every quiz (`[quiz] Generated from: ...`).

All three paths allocate the 10 questions across the four competency domains proportional to the
user's current skill-gap size (`compute_domain_weighting`).

Correct answers, explanations and citations are stored server-side on the `Assessment` row and
stripped before the quiz is sent to the client. On submit, `POST /api/v1/quiz/submit` returns a
`review` array — the full question, the learner's answer, the correct answer, the explanation and
the citation for every question — which the Results page renders as an expandable "Review Your
Answers" section.

**Compass AI** (`app/services/compass_ai_service.py`): the contextual assistant in the drawer on
the Learning page. It exposes two endpoints, both scoped by a `context` string the page passes in
— the real study material of the module the learner currently has open, not just its title:

* `POST /api/v1/compass-ai/suggestions` — three tappable starter questions for that module. If the
  LLM call fails, it degrades to generic module-aware chips rather than erroring out, so the UI
  always has something to show.
* `POST /api/v1/compass-ai/ask` — a short (under ~40 words) answer, grounded **only** in the module
  content passed in as `context`. If that content doesn't cover what was asked, the model says so
  in one sentence and suggests checking the next module or asking a trainer, instead of answering
  from its own general knowledge. `history` carries the running transcript as a flat alternating
  list (user, assistant, user, …) so follow-ups keep their referent; the transcript is cleared
  whenever the page re-grounds the assistant on a new module.

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
| POST | `/api/v1/quiz/generate` | `user_id` + optional PDF `file` → 10-question gap-weighted quiz. See "Quiz generation" above for the three-tier source logic. |
| POST | `/api/v1/quiz/submit` | `{assessment_id, user_id, answers[]}` → score + profile/passport update + per-question `review` (explanation + citation) |
| GET  | `/api/v1/analytics/dashboard` | user view for officials, aggregate view for admins |
| POST | `/api/v1/compass-ai/suggestions` | `{context}` → 3 quick-reply questions for the open module |
| POST | `/api/v1/compass-ai/ask` | `{context, question, history?}` → short contextual answer, grounded in `context` |

All endpoints except `/auth/login` require `Authorization: Bearer <token>`. Non-admin users can
only access their own `user_id` on skill-gap/recommendations/quiz endpoints (403 otherwise).

## Configuration (`.env`)

| Var | Purpose |
|---|---|
| `IGOT_MODE` | `mock` (bundled fixtures) or `live` (real iGOT HTTP endpoints) |
| `IGOT_BASE_URL`, `IGOT_API_KEY` | used only when `IGOT_MODE=live` |
| `LLM_MODEL` | LiteLLM model string, e.g. `gemini/gemini-3.6-flash` (see note below) |
| `GEMINI_API_KEY` | your Gemini API key — optional, see "Quick start" above |
| `SECRET_KEY` | JWT signing secret — change for anything beyond local demo |

## Choosing an LLM model

`LLM_MODEL` defaults to `gemini/gemini-3.6-flash`. The 2.5 family is scheduled for shutdown on
**16 October 2026** and has already returned intermittent 404s ahead of that date, which surface
in the app as `NotFoundError` from LiteLLM.

If you see an error mentioning the model was rejected by the provider, it almost always means the
model string is retired or renamed rather than a transient outage — check
<https://ai.google.dev/gemini-api/docs/models> for the current list and update `LLM_MODEL`.
Using a `-latest` alias (e.g. `gemini/gemini-flash-latest`) avoids pinning to a version that gets
retired, at the cost of the model changing under you.

Note that Gemini 3.x deprecated the `temperature`, `top_p` and `top_k` sampling parameters.
`llm_client.sampling_kwargs()` drops them automatically for 3.x and newer models and keeps sending
them for older families, so switching `LLM_MODEL` between generations needs no other code change.

## Deploying to Vercel

Vercel auto-detects the FastAPI app at `app/main.py`, so no build config is needed
beyond what's in this repo (`vercel.json` sets a longer function timeout for the
Gemini calls in quiz generation / Compass AI).

1. **Switch off SQLite.** Vercel's serverless functions have an ephemeral
   filesystem, so the bundled `sqlite:///./karmayogi_compass.db` will not persist
   between requests. Provision a Postgres database (Vercel Postgres, Neon,
   Supabase, etc.) and set `DATABASE_URL` to it, e.g.
   `postgresql://user:password@host:5432/dbname`. `psycopg2-binary` (already in
   `requirements.txt`) makes SQLModel/SQLAlchemy talk to it with no model code
   changes. `seed_service.py` checks for existing users before creating them, so
   the three demo accounts seed safely on a fresh Postgres database too.
2. **Set environment variables** in the Vercel project dashboard (values in
   `.env` are not deployed): `SECRET_KEY` (don't ship the dev default),
   `DATABASE_URL`, `GEMINI_API_KEY`, `IGOT_MODE`, and `CORS_ORIGINS` (set to your
   deployed origin instead of `*` once you have one).
3. **Deploy** by connecting the Git repo in the Vercel dashboard, or via the CLI:
```bash
   npm i -g vercel
   vercel deploy
```

## Notes / known limitations

- Production should use Postgres, not SQLite (see "Deploying to Vercel" above) — SQLModel/
  SQLAlchemy handles the dialect change with no model code changes.
- `quiz/generate`, `compass-ai/ask` and `compass-ai/suggestions` all work correctly with **no**
  `GEMINI_API_KEY` — they fall back to the built-in practice bank / generic suggestion chips
  respectively. With a working key, they upgrade automatically to AI-generated, corpus-grounded
  content; if the AI call fails mid-session for any reason, they fall back the same way rather
  than erroring out.
- Auth is JWT + bcrypt; there's no refresh-token flow or password reset — add if taking this to
  production.