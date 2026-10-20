# Software Requirements Specification (SRS): CodeReview AI

**Version:** 1.0 | **Based on:** 01_PRD.md and project documentation

---

## 1. Introduction

### 1.1 Purpose
Defines the testable functional and non-functional requirements for CodeReview AI.

### 1.2 Scope
A web application that accepts pasted source code (Python, JavaScript, HTML) and optional `requirements.txt` text, analyzes it with static analyzers, enriches findings with Claude-generated explanations, stores results, and lets users track issues, download PDF reports, and view recurring-mistake history.

### 1.3 Definitions
| Term | Meaning |
|---|---|
| Finding / Issue | One detected problem, stored as a `ReviewItem` |
| Session | One scan, stored as a `ScanSession` |
| Client ID | Random UUID generated in the browser and sent as a header; identifies a returning anonymous user |
| Review type | `quick`, `full`, or `security` |

---

## 2. User Roles and Permissions

| Role | Auth method | Permissions |
|---|---|---|
| **Student (anonymous)** | Client ID header (no password) | Submit scans; view/update own sessions and issues; download own PDF; view own history |
| **Admin** | Bearer token (`ADMIN_TOKEN` env var, or JWT from `SECRET_KEY`) | All student permissions; view analytics; edit rule toggles; edit rate limits |
| **Claude API** (external) | API key server-side | Receives finding title/description only; never receives full code unless explicitly required for a snippet |
| **CVE databases** (external) | None | Queried by Safety / pip-audit |

**Review-type behaviour**

| Type | Reviewers run |
|---|---|
| quick | Bug + Security (regex only) |
| full | Security + Quality + Practices + Bug + Dependency (if requirements given) |
| security | Security + Dependency |

---

## 3. Functional Requirements

### 3.1 Input and Validation
| ID | Requirement | Acceptance Criteria |
|---|---|---|
| FR-01 | System shall accept code, language, review type, and optional requirements text via `POST /scan`. | Valid payload returns 200 with a `session_id`. |
| FR-02 | Language shall be one of `python`, `javascript`, `html`. | Other values return 422. |
| FR-03 | Review type shall be one of `quick`, `full`, `security`. | Other values return 422. |
| FR-04 | Code length shall be 10 to 50,000 characters. | 9 chars or 50,001 chars returns 422 with message. |
| FR-05 | Whitespace-only code shall be rejected. | Returns 422. |
| FR-06 | Null bytes shall be stripped from code before processing. | Input `a\x00b...` is analyzed as `ab...`. |
| FR-07 | Requirements text shall be at most 10,000 characters. | Larger input returns 422. |
| FR-08 | Any URL field shall be checked against private ranges (10/8, 172.16/12, 192.168/16, 127/8, ::1, localhost). | Such URL returns 403 "Private/internal URLs are not permitted." |
| FR-09 | Python code shall be syntax-checked with `ast.parse` first; a syntax error is returned as a Critical finding and AST reviewers are skipped. | Broken Python yields one "Syntax error" finding with line number. |

### 3.2 Analysis
| ID | Requirement |
|---|---|
| FR-10 | **Security reviewer** shall detect: hardcoded secrets (`sk-`, `pk-`, `Bearer `, `password=`), string-formatted SQL, `eval`/`exec`, hardcoded IPs and localhost URLs, non-HTTPS requests; and shall merge Bandit JSON results for Python. |
| FR-11 | **Quality reviewer** shall run Pylint (JSON) and Radon: cyclomatic complexity > 10 is High; maintainability index < 20 is Critical; functions > 50 lines, missing docstrings, `print()` calls, and TODO comments shall be flagged. |
| FR-12 | **Bug reviewer** shall use `ast` to detect bare `except`, mutable default arguments, `== None`/`!= None`, `len(x) == 0`, `open()` outside `with`, and shadowed builtins. |
| FR-13 | **Practices reviewer** shall flag best-practice violations (wildcard imports, global state, magic numbers, missing `if __name__ == "__main__"` guard). |
| FR-14 | **Dependency reviewer** shall run Safety and pip-audit on requirements text, deduplicate by package name, and report package, installed version, safe version, CVE ID, and severity. |
| FR-15 | Each finding shall have: `category`, `severity` (Critical/High/Medium/Low), `line_no`, `title`, `description`, `fix`. |
| FR-16 | Reviewers shall run concurrently; each shall have a 20-second timeout; one reviewer failing shall not abort the scan and shall be recorded as a warning in the response. |
| FR-17 | Submitted code shall never be executed. |

### 3.3 Aggregation and Scoring
| ID | Requirement |
|---|---|
| FR-20 | Findings from all reviewers shall be merged and de-duplicated by (category, line_no, title). |
| FR-21 | Severity weights: Critical = 10, High = 7, Medium = 4, Low = 1. |
| FR-22 | `overall_score = max(0, 100 - sum(weights))`. |
| FR-23 | Grade: 90-100 = A, 70-89 = B, 50-69 = C, below 50 = F. |
| FR-24 | Findings shall be sorted Critical, High, Medium, Low, then by line number. |
| FR-25 | Response shall include `summary_counts` per severity and per category. |

### 3.4 AI Explanation
| ID | Requirement |
|---|---|
| FR-30 | The top `MAX_AI_EXPLANATIONS_PER_SCAN` (default 10) findings, prioritising Critical then High, shall be explained by Claude. |
| FR-31 | Prompt shall request a 3-sentence beginner explanation and one copy-paste code fix, language-specific. |
| FR-32 | Output shall be parsed into `{explanation, fix_code}`. |
| FR-33 | If the API key is missing, the call fails, or the rate limit is exceeded, explanation fields shall be empty strings, an `ai_status` flag shall be set, and the scan shall still succeed. |
| FR-34 | Explanations shall be cached by (rule id, language) to reduce cost. |

### 3.5 Persistence and Privacy
| ID | Requirement |
|---|---|
| FR-40 | System shall store per session: id (UUID), created_at, language, review_type, overall_score, grade, code_length, `code_hash` (SHA-256), `client_id`. |
| FR-41 | System shall **not** persist the submitted code or requirements text. |
| FR-42 | System shall store each finding as a `ReviewItem` with status default `open`. |
| FR-43 | `GET /session/{id}` shall return the stored session and items; invalid UUID returns 422; unknown id returns 404. |
| FR-44 | A session shall only be returned to the `client_id` that created it (or to admin). |

### 3.6 Issue Tracking
| ID | Requirement |
|---|---|
| FR-50 | Issue statuses: `open`, `acknowledged`, `in_progress`, `resolved`, `ignored`. (UI label "Fixed" maps to `resolved`.) |
| FR-51 | `PATCH /issue/{item_id}` shall update status; invalid transitions return 409. |
| FR-52 | Allowed transitions: open to acknowledged; acknowledged to in_progress; in_progress to open or resolved; resolved to ignored; any to ignored; ignored to open. |
| FR-53 | Re-submitting code with `parent_session_id` shall compare findings by (category, title) and report: resolved, still open, and new. Previously `in_progress` items that no longer appear shall be set to `resolved`; those still present return to `open`. |

### 3.7 Mistake History
| ID | Requirement |
|---|---|
| FR-60 | After each scan, a `MistakePattern` row for (`client_id`, language, pattern_type) shall be created or its `occurrence_count` incremented and `last_seen` updated. |
| FR-61 | `GET /history` shall return the client's patterns sorted by count descending. (Replaces `/history/{fingerprint}`; fingerprint = client ID header.) |
| FR-62 | The history view shall show the top 5 patterns with a short improvement tip each. |

### 3.8 Reporting
| ID | Requirement |
|---|---|
| FR-70 | `GET /report/{session_id}/pdf` shall return a PDF with: cover (score, grade, date), executive summary table, findings by severity with title/description/fix, and improvement suggestions. |
| FR-71 | PDF colours: Critical red, High orange, Medium yellow, Low green. |
| FR-72 | PDF generation limited to 10 per hour per IP. |

### 3.9 Admin
| ID | Requirement |
|---|---|
| FR-80 | `GET /admin/analytics` (admin token) shall return scans per day, grade distribution, and top categories. |
| FR-81 | `PUT /admin/rules` shall enable/disable individual rule IDs and persist the setting. |
| FR-82 | Admin shall be able to change `RATE_LIMIT_PER_MINUTE` and `MAX_AI_EXPLANATIONS_PER_SCAN` without code changes (env var or settings table; restart permitted). |

---

## 4. Business Rules

- BR-1: Dependency checks run only when requirements text is non-empty.
- BR-2: JavaScript and HTML receive regex-based security and practice checks only; UI shall state this.
- BR-3: A scan with zero findings scores 100 (A) and shows a congratulatory state.
- BR-4: Ignored issues still count toward score but are excluded from "open issues" counts.
- BR-5: AI is advisory; the static-analysis finding is authoritative.

## 5. Data Requirements

| Entity | Fields |
|---|---|
| **ScanSession** | id UUID PK, client_id str idx, created_at dt, language, review_type, overall_score int, grade char, code_length int, code_hash str idx, parent_session_id UUID null |
| **ReviewItem** | id UUID PK, session_id FK, category, severity, line_number int, title, description, ai_explanation text, fix_suggestion text, status, rule_id |
| **MistakePattern** | id int PK, client_id str idx, language, pattern_type, occurrence_count int, last_seen dt; unique(client_id, language, pattern_type) |
| **RuleConfig** | rule_id PK, enabled bool |

## 6. Security Requirements

| ID | Requirement |
|---|---|
| SR-01 | Rate limit `POST /scan` to 5/min/IP; PDF to 10/hour/IP; respond 429 JSON. |
| SR-02 | Set headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and CSP `default-src 'self'` (with explicit allowances for the Tailwind CDN or a self-hosted build; note the quotes around `'self'`). Drop deprecated `X-XSS-Protection`. |
| SR-03 | CORS: origins from env, `allow_credentials=False`, methods GET/POST/PATCH(/PUT admin), headers `Content-Type`, `X-Client-ID`, `Authorization`. |
| SR-04 | Use the SQLAlchemy ORM only; validate path IDs as UUIDs. |
| SR-05 | Secrets only from environment; app starts (AI disabled) if API key absent. |
| SR-06 | All user-derived text rendered in the UI shall be HTML-escaped (`textContent`, never `innerHTML`) to prevent XSS from pasted code appearing in findings. |
| SR-07 | Subprocess calls shall use argument lists (no `shell=True`), temp files with random names in a private temp dir, and be deleted in a `finally` block. |
| SR-08 | Logs shall not contain submitted code. |

## 7. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | Quick scan p95 <= 10 s; Full scan p95 <= 30 s (<= 300 lines). |
| NFR-02 | Concurrency | Supports 10 concurrent scans on free tier without crashing. |
| NFR-03 | Availability | Health endpoint `GET /health` returns 200. |
| NFR-04 | Usability | Core flow (paste to report) completable in <= 3 clicks. |
| NFR-05 | Accessibility | WCAG 2.1 AA: contrast, keyboard navigation, labels, no colour-only severity cues. |
| NFR-06 | Compatibility | Latest two versions of Chrome, Firefox, Edge, Safari; 360 px+ width. |
| NFR-07 | Maintainability | Reviewers share an abstract `Reviewer` base class; adding a reviewer requires no change to the aggregator. |
| NFR-08 | Testability | >= 70% line coverage on reviewers and aggregator. |
| NFR-09 | Portability | Runs via `uvicorn` on Python 3.11+ with SQLite; `DATABASE_URL` allows swapping to Postgres. |

## 8. Error Handling

| Situation | Behaviour |
|---|---|
| Validation failure | 422 with field-level messages |
| Rate limit | 429 `{"detail": "Rate limit exceeded. Try again in N seconds."}` |
| Reviewer timeout/crash | Scan continues; response contains `warnings: ["security reviewer timed out"]` |
| Claude API error | Empty explanation, `ai_status = "unavailable"`, UI shows notice |
| DB error | 500 generic message; details logged server-side |
| Session not found / not owned | 404 (do not reveal existence) |

## 9. Edge Cases

- Pasted code in a different language than selected: show a "language mismatch" warning when `ast.parse` fails on Python selection and the code looks like JS.
- Very long single line (minified code): flag as Low "readability" and cap processing.
- Code with zero functions: skip complexity checks without error.
- Duplicate scan of identical code: new session created; hash match noted but no code retrieved.
- Unicode / emoji / CRLF line endings: normalised before analysis; line numbers remain accurate.
- Requirements with unpinned versions: treated as "latest", flagged Low "pin your versions".
- Concurrent PATCH on one issue: last write wins; response returns the current state.
- Browser storage cleared: client ID regenerated; user sees empty history (explained in UI).

## 10. Acceptance Test Summary

| Test | Input | Expected |
|---|---|---|
| T1 | `eval(input())` | High/Critical finding, line number, fix |
| T2 | `def f(x=[]):` | Mutable-default finding |
| T3 | `password = "abc123"` | Hardcoded secret finding |
| T4 | 50,001 chars | 422 |
| T5 | 6 scans in 60 s | 6th returns 429 |
| T6 | Anthropic key unset | Scan succeeds; `ai_status` = unavailable |
| T7 | Mark issue resolved, refresh | Status persists |
| T8 | Re-submit fixed code | Fixed issues reported resolved |
| T9 | `<script>alert(1)</script>` in a code comment | Rendered as text, not executed |
| T10 | DB inspection | No raw code stored |