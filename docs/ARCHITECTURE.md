# System Architecture Document: CodeReview AI

**Version:** 1.0 | **Based on:** 01_PRD.md, 02_SRS.md

Principle: a **modular monolith**. One FastAPI process, one SQLite file, static frontend. No queues, containers, or microservices are needed at this scale.

---

## 1. Recommended Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language / runtime | Python 3.11+ | Same language as the analyzers |
| Web framework | FastAPI + Uvicorn | Async, automatic validation, OpenAPI docs |
| Validation | Pydantic v2, pydantic-settings | Strict schemas, env config |
| Database | SQLite via SQLAlchemy ORM (Postgres-ready via `DATABASE_URL`) | Zero setup |
| Static analysis | Bandit, Pylint, Radon, Pyflakes, `ast` | Industry-standard Python tooling |
| Dependency audit | Safety, pip-audit | Two CVE sources |
| AI | Anthropic Python SDK (Claude) | Beginner-friendly explanations |
| PDF | ReportLab | Pure Python |
| Rate limiting | SlowAPI | Simple per-IP limits |
| Frontend | HTML, vanilla JS, Tailwind (compiled CSS preferred, CDN acceptable for lab) | No build chain |
| Hosting | Render (primary), Railway (alternative) | Free tier |

## 2. High-Level Architecture

```
 Browser (index.html / review.html / report.html / history.html)
        |  HTTPS, JSON, X-Client-ID header
        v
 +---------------------- FastAPI app (backend/main.py) ----------------------+
 |  Middleware: CORS | Security headers | SlowAPI | Request-size guard       |
 |                                                                           |
 |  Routers:  /scan  /session  /issue  /report  /history  /admin  /health    |
 |      |                                                                    |
 |  Orchestrator (scan service)                                              |
 |      |--> Reviewers (parallel, subprocess + timeout)                      |
 |      |       security | quality | practices | bug | dependency            |
 |      |--> Aggregator (merge, dedupe, score, grade, pick top N)            |
 |      |--> AIExplainer --> Claude API (external, optional)                 |
 |      |--> Repository layer (SQLAlchemy) --> SQLite                        |
 |      '--> Report generator (ReportLab) --> PDF bytes                      |
 +---------------------------------------------------------------------------+
        External: Anthropic API, CVE feeds (via Safety / pip-audit)
```

## 3. Components

| Component | File | Responsibility |
|---|---|---|
| Entry / routing | `main.py` | App factory, middleware, routes |
| Config | `config.py` | `Settings` (pydantic-settings) |
| DB | `database.py`, `models.py` | Engine, session dependency, ORM models |
| Schemas | `schemas.py` | Request/response validation |
| Auth / limits | `auth.py` | Client ID parsing, admin token check, limiter instance |
| Reviewer base | `reviewers/base.py` (add) | Abstract `Reviewer.analyze()` and shared finding factory |
| Reviewers | `reviewers/*.py` | Each returns `list[Finding]` |
| Aggregator | `aggregator.py` | Merge, dedupe, score, sort, select for AI |
| Explainer | `explainer.py` | Claude calls, parsing, caching, failure isolation |
| Report | `report.py` | PDF bytes |
| Security helpers | `security_utils.py` (add) | `is_private_ip`, UUID validation, sanitizers |

**Finding contract (internal and API)**
```json
{
  "rule_id": "SEC001",
  "category": "security",
  "severity": "High",
  "line_no": 12,
  "title": "Use of eval()",
  "description": "...",
  "fix": "...",
  "ai_explanation": "",
  "fix_code": ""
}
```

## 4. API Design

All JSON. Header `X-Client-ID: <uuid>` on every student request.

| Method | Path | Purpose | Notes |
|---|---|---|---|
| POST | `/scan` | Run a review | Body: `code, language, review_type, requirements?, parent_session_id?`. Limit 5/min/IP. Returns report |
| GET | `/session/{id}` | Fetch stored session + items | UUID-validated, owner-checked |
| PATCH | `/issue/{item_id}` | Update status | Body: `{status}` |
| GET | `/report/{id}/pdf` | PDF download | 10/hour/IP |
| GET | `/history` | Recurring patterns for client | Uses `X-Client-ID` |
| GET | `/sessions` | List client's recent sessions | For "my reviews" list |
| GET | `/admin/analytics` | Aggregate stats | Admin token |
| PUT | `/admin/rules` | Toggle rules | Admin token |
| GET | `/health` | Liveness | No auth |

**Scan response (abridged)**
```json
{
  "session_id": "uuid",
  "overall_score": 62,
  "grade": "C",
  "summary_counts": {"Critical": 1, "High": 3, "Medium": 4, "Low": 2},
  "findings": [ ... ],
  "warnings": [],
  "ai_status": "ok",
  "comparison": null
}
```

## 5. Data Flow: Scan Request

1. Browser POSTs to `/scan` with the client ID.
2. Middleware applies rate limit and size guard; Pydantic validates the body.
3. Code is normalised (strip nulls, normalise newlines); SHA-256 hash is computed.
4. The orchestrator selects reviewers for the review type and runs them concurrently (`asyncio.gather`, with blocking subprocess calls wrapped in `run_in_executor` or `asyncio.to_thread`). Each has a timeout.
5. The aggregator merges, de-duplicates, scores, grades, and sorts.
6. The explainer enriches the top N findings (concurrently, bounded by a semaphore of 3). Failures are swallowed into `ai_status`.
7. Repository saves `ScanSession` + `ReviewItem`s (**no code**), then upserts `MistakePattern`.
8. If `parent_session_id` is present, a comparison is computed and returned.
9. The response is returned; the frontend redirects to `review.html?session=<id>`.

## 6. Database Design

```
ScanSession 1 ---- N ReviewItem
     |
     '-- client_id ---- N MistakePattern (unique client_id + language + pattern_type)

RuleConfig (rule_id, enabled)
```
Indexes: `ScanSession.client_id`, `ScanSession.code_hash`, `ReviewItem.session_id`, `MistakePattern.client_id`.
Migrations: Alembic recommended; `Base.metadata.create_all()` acceptable for the lab.
SQLite note: enable `PRAGMA foreign_keys=ON`. On Render's free tier the filesystem is ephemeral, so data resets on redeploy. Use a Render Postgres free instance or accept the limitation and state it in the README.

## 7. Authentication and Authorization

- **Students:** no login. A UUIDv4 `client_id` is generated in `localStorage` and sent as `X-Client-ID`. Ownership checks compare session `client_id` to the header. This is *identification, not authentication*; session UUIDs are unguessable but anyone holding the client ID can access that history. This is documented as an accepted MVP trade-off.
- **Admin:** `Authorization: Bearer <ADMIN_TOKEN>` compared with `hmac.compare_digest`. (JWT via `python-jose` is only needed if multi-admin is added; for MVP a static token suffices, so `passlib` and `python-jose` can be dropped from requirements.)
- **Upgrade path:** email/OAuth login would map existing `client_id` to a user row.

## 8. Security Architecture

| Threat | Control |
|---|---|
| Malicious code exploiting analyzers | Never execute code; `ast.parse` only; Bandit/Pylint run on a temp file in a private temp dir with timeout; subprocess uses arg lists; optional resource limits (`resource.setrlimit`) on POSIX |
| Prompt injection via pasted code reaching Claude | Send only finding title/description plus a short, length-capped snippet; system prompt tells Claude to treat snippet as data; output parsed strictly |
| XSS | Frontend uses `textContent`; CSP `default-src 'self'` with no inline scripts (use external JS files); self-host Tailwind build to avoid CDN allowance |
| Abuse / cost | SlowAPI limits, AI cap per scan, explanation cache |
| SSRF | `is_private_ip` on any URL field; no server-side URL fetching in MVP |
| Secrets | `.env` ignored by Git; host dashboard env vars |
| Data privacy | No code stored; hash only; no code in logs |
| Injection | ORM only; UUID path validation |
| CORS | Explicit origins from env, no credentials |
| Dependencies | `pip-audit`, `safety`, `bandit -r backend/` in a pre-deploy checklist |

## 9. Storage

- Relational data: SQLite file (`codereview.db`).
- Temp files: OS temp dir, deleted in `finally`.
- PDFs: generated on demand in memory, not stored.
- No object storage required.

## 10. Deployment Architecture

```
GitHub repo --> Render Web Service
                 build: pip install -r requirements.txt
                 start: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
                 env:   ANTHROPIC_API_KEY, DATABASE_URL, SECRET_KEY,
                        ADMIN_TOKEN, ALLOWED_ORIGINS, RATE_LIMIT_PER_MINUTE,
                        MAX_AI_EXPLANATIONS_PER_SCAN
Frontend served by FastAPI StaticFiles from the same origin (no CORS needed in prod).
```
- Single instance, one Uvicorn worker (SQLite and in-memory rate limiter assume this).
- Pin Python version via `runtime.txt` / `PYTHON_VERSION`.
- Bandit, Pylint, Radon, Safety, and pip-audit must be in `requirements.txt`, not only dev dependencies.

## 11. Monitoring and Logging

- Structured logs (JSON) with request id, route, latency, reviewer durations, AI success/failure; never log code.
- `/health` for uptime pings (UptimeRobot free tier also prevents cold sleep).
- Admin analytics endpoint doubles as lightweight product monitoring.
- Optional: Sentry free tier for exceptions.

## 12. Scalability Path (documented, not built)

| Bottleneck | Next step |
|---|---|
| CPU-bound analyzers | Background workers (RQ/Celery) with job polling, `POST /scan` returns job id |
| SQLite writes / ephemeral disk | Managed Postgres |
| In-memory rate limits | Redis backend for SlowAPI |
| AI latency | Stream explanations or load them lazily per card |
| More languages | Add Reviewer subclasses (ESLint, Semgrep) behind the same contract |

## 13. Design Decisions and Corrections to Source Documentation

| Source doc item | Decision |
|---|---|
| CSP `default-src self` | Must be `'self'` (quoted); Tailwind CDN needs allowance or self-host |
| `X-XSS-Protection` | Deprecated; omit (CSP covers this) |
| `/history/{fingerprint}` with code hash | A code hash changes with any edit, so it cannot detect recurring mistakes; use `client_id` + pattern type |
| Issue states differ between state chart and API | Unified to: open, acknowledged, in_progress, resolved, ignored |
| `python-jose`, `passlib` in requirements | Unnecessary without user accounts; removed |
| `requests` and `httpx` | Only needed if URL scanning is added; drop for MVP |
| Parallel reviewers via `asyncio.gather` | Subprocess work must be wrapped in threads to avoid blocking the event loop |