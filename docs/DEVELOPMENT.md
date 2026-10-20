# Development Plan: CodeReview AI

**Version:** 1.0 | **Based on:** 01_PRD.md, 02_SRS.md, 03_Architecture.md, 04_UI_UX.md
**Assumption:** one to three students, about 10-15 hours per week, roughly 6 weeks to a deployed MVP. Adjust the week count to your lab deadline.

---

## 1. MVP Scope

**In (must ship):** paste and validate; security, quality, bug, and practices reviewers (Python), basic JS/HTML regex checks; aggregator with score and grade; Claude explanations with graceful fallback; SQLite persistence (no code stored); review board with status tracking; rate limiting, security headers, CORS; deployment.

**Next (should, if time permits):** dependency checker, re-scan comparison, PDF report, mistake history.

**Later (could):** admin analytics and rule toggles, dark mode, ESLint integration, accounts.

## 2. Roadmap Overview

| Phase | Week | Outcome |
|---|---|---|
| 0. Setup | 1 | Repo, environment, skeleton app runs |
| 1. Backend core | 1-2 | DB, schemas, config, middleware |
| 2. Reviewers | 2-3 | All reviewers pass unit tests on sample bad code |
| 3. Aggregation and AI | 3-4 | End-to-end `POST /scan` works |
| 4. Frontend | 4-5 | Home and review board functional |
| 5. Extras | 5 | Re-scan, PDF, history |
| 6. Hardening and testing | 5-6 | Security checklist, bug fixing |
| 7. Deployment and docs | 6 | Live URL, README, lab record |

## 3. Detailed Tasks

### Phase 0: Setup (Week 1)
- [ ] Create the folder structure from the documentation; add `reviewers/base.py` and `security_utils.py`.
- [ ] `git init`; `.gitignore` with `.env`, `venv/`, `*.db`, `__pycache__/`.
- [ ] Create venv; write `requirements.txt` (drop `python-jose`, `passlib`, `requests`; keep `httpx` only if needed; add `pip-audit`, `pydantic-settings`, `pytest`); pin versions after a successful install.
- [ ] `config.py` with `Settings`; `.env.example` committed.
- [ ] Minimal `main.py` with `/health`; confirm `uvicorn backend.main:app --reload` runs.
- [ ] Create `tests/sample_bad_code.py` containing one example of every issue you plan to detect (the project's ground truth).

**Done when:** `/health` returns 200 locally and the repo is on GitHub without secrets.

### Phase 1: Backend Core (Weeks 1-2)
- [ ] `database.py`: engine, `SessionLocal`, `get_db` dependency, SQLite foreign key pragma.
- [ ] `models.py`: `ScanSession`, `ReviewItem`, `MistakePattern`, `RuleConfig` with `code_hash`, `client_id`.
- [ ] `schemas.py`: `ScanRequest` with validators (null bytes, whitespace-only), response models, status enum.
- [ ] `auth.py`: `get_client_id` dependency (validate UUID), `require_admin`, limiter instance.
- [ ] Middleware: security headers (correct CSP quoting), CORS, SlowAPI with JSON 429 handler.
- [ ] `security_utils.py`: `is_private_ip`, `validate_uuid`.

**Done when:** schema tests pass; 6th request in a minute returns 429; headers present.

### Phase 2: Reviewers (Weeks 2-3)
Order by value and simplicity:
1. [ ] `base.py`: abstract `Reviewer`, `Finding` helper.
2. [ ] `bug_reviewer.py` (AST): bare except, mutable defaults, `== None`, `len(x)==0`, `open()` without `with`, builtin shadowing.
3. [ ] `security_reviewer.py`: regex rules first, then Bandit subprocess (JSON, temp file, timeout, cleanup in `finally`).
4. [ ] `quality_reviewer.py`: Radon CC and MI, long functions, `print`, TODO, then Pylint JSON.
5. [ ] `practices_reviewer.py`: docstrings, wildcard imports, magic numbers, main guard.
6. [ ] `dep_reviewer.py`: Safety and pip-audit, dedupe (build last; these tools need network access).
7. [ ] JS/HTML regex rule set (inline event handlers, `innerHTML`, `eval`, `http://`, hardcoded keys).
8. [ ] Per-reviewer unit tests asserting every seeded issue in `sample_bad_code.py` is found, plus clean-code tests that expect zero false positives.

**Done when:** each reviewer returns the standard finding format; timeouts verified by a test that feeds a slow stub.

### Phase 3: Aggregator, AI, and Scan Endpoint (Weeks 3-4)
- [ ] `aggregator.py`: merge, dedupe, score, grade, sort, select top N; unit tests for boundary scores (49/50, 69/70, 89/90) and score floor.
- [ ] `explainer.py`: Anthropic SDK, strict prompt, output parser, cache, semaphore, try/except around everything; test with API key unset and with a mocked failure.
- [ ] Orchestrator in `main.py` or `services/scan.py`: reviewer selection by review type, `asyncio.to_thread` plus `gather`, warnings collection.
- [ ] Persistence: save session and items (no code), upsert `MistakePattern`.
- [ ] Routes: `POST /scan`, `GET /session/{id}`, `PATCH /issue/{id}` with transition rules, `GET /history`, `GET /sessions`.
- [ ] Integration tests with FastAPI `TestClient`.

**Done when:** a curl request with `sample_bad_code.py` returns a complete report in under 30 s, and the DB shows no raw code.

### Phase 4: Frontend (Weeks 4-5)
- [ ] `style.css` tokens and base styles; Tailwind setup (compiled CSS preferred).
- [ ] `app.js`: client ID bootstrap, validation, counter, submit with fetch, stepper, error and 429 handling, redirect.
- [ ] `index.html` per the UI/UX spec.
- [ ] `review.js` and `review.html`: fetch session, score ring, severity chips, grouped cards, filters, copy button, status PATCH with optimistic update and rollback.
- [ ] `history.html` and `history.js`.
- [ ] Accessibility pass: keyboard walk-through, contrast check, screen-reader labels.
- [ ] Mobile check at 360 px width.

**Done when:** the full flow works in the browser from paste to status update with no console errors.

### Phase 5: Extras (Week 5)
- [ ] Re-scan: `parent_session_id`, comparison logic, banner UI.
- [ ] `report.py`: ReportLab PDF with cover, summary table, severity sections, suggestions; `GET /report/{id}/pdf` with 10/hour limit.
- [ ] `report.html` print view.
- [ ] Admin analytics endpoint (if time permits).

### Phase 6: Hardening and Testing (Weeks 5-6)
- [ ] Security checklist: `bandit -r backend/`, `pip-audit`, `safety check`; fix Critical and High.
- [ ] Verify CSP does not break the UI; confirm no inline scripts.
- [ ] XSS test: put `<img src=x onerror=alert(1)>` in code and comments; ensure it renders as text.
- [ ] Subprocess abuse tests: huge input, deeply nested code, `__import__('os').system(...)` strings (must never execute).
- [ ] Owner-check tests: client B cannot read client A's session.
- [ ] Load smoke test with 10 concurrent scans.
- [ ] Run the acceptance tests T1-T10 from the SRS.

### Phase 7: Deployment and Documentation (Week 6)
- [ ] Push to GitHub; create Render web service; set env vars; confirm start command.
- [ ] Decide database persistence (Render Postgres free, or accept ephemeral SQLite and document it).
- [ ] Add a health-check ping (UptimeRobot) to reduce cold starts.
- [ ] Smoke test the live URL, including PDF and 429 behaviour.
- [ ] `README.md`: overview, screenshots, setup, env vars, test commands, limitations.
- [ ] Redraw UML diagrams in draw.io from the documentation for the lab record; update if the design changed (client ID, unified statuses).

## 4. Dependencies and Critical Path

```
Setup -> DB/Schemas -> Reviewers -> Aggregator -> /scan endpoint -> Frontend board
                             \-> Explainer (parallel) ---^
                                              /scan -> Re-scan, PDF, History
```
- The frontend can start against a mocked JSON response once the response contract is fixed (end of Phase 1), so UI work need not wait for the reviewers.
- Dependency reviewer, PDF, and admin are off the critical path and can slip without blocking the demo.
- External dependencies: Anthropic API key and credits; Render account; network access for Safety/pip-audit.

## 5. Milestones

| # | Milestone | Target | Evidence |
|---|---|---|---|
| M1 | Skeleton running | End of week 1 | `/health` works, repo pushed |
| M2 | Reviewers complete | End of week 3 | Unit tests green on sample bad code |
| M3 | End-to-end scan | End of week 4 | curl returns a scored, explained report |
| M4 | Usable UI | Mid week 5 | Browser flow works, status persists |
| M5 | Feature-complete MVP+ | End of week 5 | Re-scan, PDF, history |
| M6 | Hardened | Early week 6 | Security checklist clear, tests pass |
| M7 | Live demo | End of week 6 | Public URL, README, lab record |

## 6. Testing Strategy

| Level | Tooling | Coverage target |
|---|---|---|
| Unit | pytest | Reviewers, aggregator, validators, transitions (>= 70%) |
| Integration | FastAPI TestClient, mocked Claude | All routes, error paths |
| Security | Bandit, pip-audit, safety, manual XSS/ownership tests | All SRS security requirements |
| UI / manual | Checklist on Chrome, Firefox, mobile width | All screens, all states |
| Acceptance | SRS T1-T10 | 100% pass |

**Test data:** `sample_bad_code.py` (every seeded issue, with an expected-findings list), a clean file (expect score near 100), a syntax-error file, and a 50,001-character file.

## 7. Bug-Fixing Protocol

- Track bugs as GitHub Issues labelled `severity:*` and `area:*`.
- Fix order: data loss or security, then blocked core flow, then wrong results, then UI polish.
- Every fixed bug gets a regression test where practical.
- Freeze new features at the start of week 6; only fixes after that.

## 8. Risk Watch-list

| Risk | Trigger | Response |
|---|---|---|
| Pylint and Bandit slow or timing out | Full scan over 30 s | Run in parallel, trim Pylint rules to a curated set, lower timeouts |
| Claude cost/latency | Slow or failing calls | Reduce `MAX_AI_EXPLANATIONS_PER_SCAN`, rely on cache and fallback |
| Free-tier ephemeral storage | Data disappears after redeploy | Move to hosted Postgres or document |
| Scope creep | Extras not started by week 5 | Cut admin, dark mode, JS depth |
| Team time shortage | Milestone slips by more than a week | Drop dependency reviewer and PDF; keep the core flow |

## 9. Definition of Done

**Per task:** code reviewed (or self-reviewed against the SRS ID), unit tests added and passing, no new Bandit High findings, no secrets committed, docstrings on public functions.

**Per feature:** acceptance criteria in the SRS met, error and empty states handled, accessible via keyboard, works at 360 px width.

**For the MVP release:**
1. All PRD acceptance criteria (section 10) pass.
2. SRS tests T1-T10 pass locally and on the deployed URL.
3. `bandit -r backend/`, `pip-audit`, and `safety check` show no Critical/High issues.
4. No raw submitted code in the database or logs.
5. README lets a new person run the app in under 10 minutes.
6. Deployed on a public free-tier URL with env vars set (no secrets in the repo).
7. UML diagrams and the five project documents are updated to match the final implementation.

## 10. Suggested Weekly Checklist (copy into your tracker)

- **Week 1:** Phase 0 plus start Phase 1
- **Week 2:** Finish Phase 1; bug and security reviewers
- **Week 3:** Remaining reviewers and tests
- **Week 4:** Aggregator, explainer, `/scan`, start frontend with mock data
- **Week 5:** Frontend complete; re-scan, PDF, history
- **Week 6:** Hardening, deployment, README, lab record