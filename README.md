# CodeReview AI

**Automated code review for AI-generated code, built for students.**

Paste your code, get a teacher-style review: a score, a grade, findings grouped by severity, plain-English explanations from Claude, and copy-paste fixes. No Git repo, no CI pipeline, no sign-up.

> Software Engineering Lab, CS3007 | 2026-27 Odd Semester

---

## Why CodeReview AI?

Tools like SonarQube and CodeRabbit need repositories and pipelines. CodeReview AI accepts raw pasted code and explains problems to beginners. It also tracks the mistakes you repeat across sessions and shows them in a personal history, which most review tools don't do.

## Features

- **Paste and review** Python, JavaScript, or HTML in Quick, Full, or Security-only mode
- **Security checks:** hardcoded secrets, SQL injection patterns, `eval`/`exec`, hardcoded IPs, non-HTTPS calls (Bandit + regex)
- **Quality checks:** complexity, maintainability, long functions, naming, leftover `print()` and TODOs (Pylint + Radon)
- **Bug detection:** bare `except`, mutable default arguments, `== None`, unclosed files, shadowed builtins (AST)
- **Dependency audit:** known CVEs from `requirements.txt` (Safety + pip-audit)
- **AI explanations:** 3-sentence beginner explanation plus a code fix for the top findings (Claude)
- **Issue tracker:** mark each finding open, acknowledged, in progress, resolved, or ignored
- **Re-scan:** re-submit fixed code and see what was resolved
- **PDF report** download
- **Mistake history:** your most frequent problems over time
- **Privacy-first:** your code is not stored, only a SHA-256 hash and metadata

> JavaScript and HTML get regex-based checks only. Deep analysis is Python-only.

## Tech Stack

| Layer | Tools |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy, Pydantic, SlowAPI |
| Analysis | Bandit, Pylint, Radon, Pyflakes, `ast`, Safety, pip-audit |
| AI | Anthropic Python SDK (Claude) |
| Reports | ReportLab |
| Frontend | HTML, vanilla JavaScript, Tailwind CSS |
| Database | SQLite (Postgres-ready via `DATABASE_URL`) |

## Project Structure

```
codereview-ai/
├── backend/
│   ├── main.py            # FastAPI app and routes
│   ├── config.py          # Settings from .env
│   ├── database.py        # SQLAlchemy setup
│   ├── models.py          # ORM models
│   ├── schemas.py         # Pydantic models
│   ├── auth.py            # Client ID, admin token, rate limiter
│   ├── aggregator.py      # Merge, score, grade
│   ├── explainer.py       # Claude integration
│   ├── report.py          # PDF generation
│   └── reviewers/         # security, quality, practices, bug, dependency
├── frontend/
│   ├── index.html         # Paste code
│   ├── review.html        # Review board
│   ├── report.html        # Report view
│   ├── history.html       # My mistakes
│   ├── css/style.css
│   └── js/                # app.js, review.js, history.js
├── tests/
│   ├── test_security.py
│   ├── test_quality.py
│   └── sample_bad_code.py # Known-bad code with seeded issues
├── .env.example
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or newer
- An [Anthropic API key](https://console.anthropic.com/) (optional: without it the app still works, but AI explanations are disabled)
- Git

### Installation

```bash
git clone <your-repo-url>
cd codereview-ai

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Copy the example file and edit it:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (optional) | none |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./codereview.db` |
| `SECRET_KEY` | Random secret for signing | required |
| `ADMIN_TOKEN` | Bearer token for admin endpoints | none (admin disabled) |
| `ALLOWED_ORIGINS` | JSON list of allowed CORS origins | `["http://localhost:8000"]` |
| `RATE_LIMIT_PER_MINUTE` | Scans per minute per IP | `5` |
| `MAX_AI_EXPLANATIONS_PER_SCAN` | Findings explained by Claude per scan | `10` |

**Never commit `.env`.** It is listed in `.gitignore`.

### Run

```bash
uvicorn backend.main:app --reload
```

Open <http://localhost:8000>. Interactive API docs are at <http://localhost:8000/docs>.

## Usage

1. Open the home page and paste your code.
2. Choose the language and review type (Quick, Full, or Security-only).
3. For Python, optionally paste your `requirements.txt` to check dependencies.
4. Click **Review my code**.
5. On the review board, read each finding, copy the suggested fix, and update the status.
6. Fix your code and choose **Re-submit fixed code** to compare results.
7. Download the PDF report or open **My Mistakes** to see your recurring patterns.

### Scoring

| Severity | Points deducted |
|---|---|
| Critical | 10 |
| High | 7 |
| Medium | 4 |
| Low | 1 |

`Score = max(0, 100 - total deductions)`. Grades: **A** 90-100, **B** 70-89, **C** 50-69, **F** below 50.

### Review types

| Type | What runs |
|---|---|
| Quick | Bug and security (regex) checks |
| Full | All reviewers, plus dependency audit if requirements are given |
| Security-only | Security and dependency checks |

## API Overview

All student requests send an `X-Client-ID` header (a UUID the browser generates automatically).

| Method | Endpoint | Description |
|---|---|---|
| POST | `/scan` | Run a review (5/min per IP) |
| GET | `/session/{id}` | Fetch a stored review |
| GET | `/sessions` | List your recent reviews |
| PATCH | `/issue/{id}` | Update an issue's status |
| GET | `/report/{id}/pdf` | Download PDF (10/hour per IP) |
| GET | `/history` | Your recurring mistake patterns |
| GET | `/admin/analytics` | Aggregate stats (admin token) |
| GET | `/health` | Health check |

Example:

```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -H "X-Client-ID: 3f2b8c1e-9d4a-4e7b-8a21-6c5d0e1f7a90" \
  -d '{"code": "def f(x=[]):\n    return eval(x)", "language": "python", "review_type": "full"}'
```

## Testing

```bash
pytest                              # all tests
pytest tests/test_security.py       # one file
```

`tests/sample_bad_code.py` contains one example of every issue the reviewers should catch and serves as the ground truth for detection tests.

## Security

- Submitted code is **never executed** and **never stored** (only language, review type, length, and a SHA-256 hash)
- Rate limiting on `/scan` and PDF endpoints, with HTTP 429 responses
- Security headers and a strict Content-Security-Policy
- Strict CORS, no credentials
- ORM-only database access; UUID validation on path parameters
- Private/internal URLs are blocked
- User-derived text is rendered with `textContent` to prevent XSS
- Secrets are read from environment variables only

Before deploying, scan your own code:

```bash
bandit -r backend/
pip-audit
safety check
```

## Deployment (Render, free tier)

1. Push the repo to GitHub (confirm `.env` is ignored).
2. On [render.com](https://render.com): **New > Web Service**, connect the repo.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add the environment variables from the table above in the Render dashboard.
6. Deploy, then check `/health`.

Railway also works: `railway login`, `railway init`, `railway up`, then `railway variables set ANTHROPIC_API_KEY=...`.

> **Note:** SQLite data on free tiers can be wiped on redeploy. Use a hosted Postgres database via `DATABASE_URL` if you need persistence.

## Known Limitations

- Single-file analysis only (no multi-file projects)
- Python has full analysis; JavaScript and HTML use regex rules only
- No user accounts: history is tied to your browser's anonymous client ID, so clearing browser storage resets it
- AI fixes are suggestions and should be reviewed before use
- Free-tier hosting may be slow on the first request after idle time

## Roadmap

- ESLint integration for JavaScript
- Multi-file and ZIP upload
- Optional accounts and login
- Classroom view for instructors
- Background job queue for long scans

## Documentation

Detailed design documents are in the `docs/` folder:

- `01_PRD.md` Product Requirements
- `02_SRS.md` Software Requirements Specification
- `03_Architecture.md` System Architecture
- `04_UI_UX.md` UI/UX Design
- `05_Development_Plan.md` Development Plan

## Contributing

1. Fork the repo and create a branch: `git checkout -b feature/your-feature`
2. Add tests for your change and make sure `pytest` passes
3. Run `bandit -r backend/` and fix any High findings
4. Open a pull request describing the change

## License

Add your license here (for example, MIT) before making the repository public.

## Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [Bandit](https://bandit.readthedocs.io/), [Pylint](https://pylint.readthedocs.io/), [Radon](https://radon.readthedocs.io/), [ReportLab](https://www.reportlab.com/), and [Claude](https://www.anthropic.com/) by Anthropic.