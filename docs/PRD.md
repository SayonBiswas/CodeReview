# Product Requirements Document (PRD): CodeReview AI

**Version:** 1.0 | **Course:** Software Engineering Lab, CS3007 (2026-27 Odd Semester) | **Status:** Draft for implementation

---

## 1. Product Summary

CodeReview AI is a web-based automated code review tool for students who write code with AI assistants ("vibe coding"). The student pastes raw source code, with no Git repo or CI pipeline, and gets back a structured, teacher-style review: scored findings, plain-English explanations, copy-paste fixes, and a personal history of recurring mistakes.

## 2. Problem Statement

- Students increasingly ship AI-generated code they do not fully understand, so insecure patterns, bugs, and poor practices go unnoticed.
- Enterprise tools (SonarQube, CodeRabbit) require repositories, CI/CD, and configuration, which is a barrier for lab students and hobbyists.
- Existing linters output cryptic messages aimed at experienced developers and do not teach.
- No tool tracks *which mistakes a learner keeps repeating* over time.

## 3. Target Users

| Persona | Description | Key Need |
|---|---|---|
| **Primary: CSE lab student** | 2nd-4th year, uses ChatGPT/Claude/Copilot to write code, no Git workflow | Fast, understandable feedback on pasted code |
| **Secondary: Hobbyist / early builder** | Builds side projects, no CI | Quick security and quality sanity check |
| **Tertiary: Admin (course instructor)** | Maintains the instance | Tune rules, see aggregate analytics, control rate limits |

## 4. Goals and Non-Goals

### Goals
1. Return a complete review of pasted code in under 30 seconds (Quick mode under 10 seconds).
2. Explain every high-priority finding to a beginner in plain English with a concrete fix.
3. Let users track the lifecycle of each issue (open to resolved) and re-scan fixed code.
4. Surface recurring mistake patterns per user across sessions (**the differentiator**).
5. Protect user privacy: do not store submitted source code.

### Non-Goals (Out of Scope for MVP)
- Git/GitHub integration, PR comments, CI/CD plugins
- Multi-file or whole-project upload (single paste only)
- Languages beyond Python, JavaScript, HTML
- Real-time collaboration, teams, or classroom management
- Auto-applying fixes to code
- Mobile app (responsive web only)
- Paid plans / billing

## 5. Core Features

| # | Feature | Priority | Notes |
|---|---|---|---|
| F1 | Code paste interface with language and review-type selection | Must | Quick / Full / Security-only |
| F2 | Security scanner (Bandit + regex rules) | Must | Secrets, SQLi, eval/exec, hardcoded IPs, non-HTTPS |
| F3 | Quality analyzer (Pylint + Radon) | Must | Complexity, maintainability, naming, long functions |
| F4 | Bug detector (AST-based) | Must | Bare except, mutable defaults, `== None`, unclosed files, shadowed builtins |
| F5 | Best-practice checks | Should | Missing docstrings, leftover `print()`, TODOs |
| F6 | Dependency CVE checker (Safety + pip-audit) | Should | Only when requirements text is supplied |
| F7 | Aggregator with scoring and grading | Must | Score = 100 minus weighted severity, grades A/B/C/F |
| F8 | AI explanations (Claude API) | Must | Top N findings; graceful fallback if unavailable |
| F9 | Review board with issue status tracking | Must | Per-issue status dropdown |
| F10 | Re-submit and re-scan with comparison | Should | Shows resolved vs. new issues |
| F11 | PDF report download | Should | ReportLab, colour-coded by severity |
| F12 | Personal mistake history | Should | Differentiator; anonymous client ID based |
| F13 | Admin rule configuration and analytics | Could | Basic, token-protected |

## 6. User Stories

**Submission**
- As a student, I want to paste my code and pick a language so that I get a review without any setup.
- As a student, I want to choose Quick, Full, or Security-only so that I can trade depth for speed.
- As a student, I want to optionally paste `requirements.txt` so that vulnerable dependencies are flagged.

**Review**
- As a student, I want an overall score and grade so that I immediately know how my code stands.
- As a student, I want findings grouped by severity so that I fix the worst problems first.
- As a student, I want each finding explained in plain English with a fix I can copy so that I learn rather than just patch.

**Tracking**
- As a student, I want to mark an issue acknowledged, in progress, fixed, or ignored so that I can manage my work.
- As a student, I want to re-submit corrected code and see what got fixed and what is new.
- As a student, I want to see my most frequent mistakes over time so that I can improve deliberately.

**Export**
- As a student, I want to download a PDF report so that I can attach it to a lab submission.

**Admin**
- As an admin, I want to adjust rate limits and enable or disable rules so that I can protect the service and tune strictness.
- As an admin, I want aggregate analytics (scans/day, top issue categories) so that I can see how students use the tool.

## 7. Success Metrics

| Metric | Target (demo / lab evaluation) |
|---|---|
| Detection accuracy on `sample_bad_code.py` (known seeded issues) | >= 90% of seeded issues detected |
| Full-scan latency (p95, code <= 300 lines) | <= 30 s including AI explanations |
| AI explanation success rate | >= 95% of requested explanations returned |
| Scan pipeline survives AI outage | 100% (raw findings still shown) |
| Users who open a second session within 7 days (pilot with classmates) | >= 40% |
| Issues moved to Resolved after re-scan (pilot) | >= 50% of issues viewed |
| Stored source code in DB | 0 bytes (hash and metadata only) |

## 8. Assumptions

- Users have a modern browser and internet access.
- Python is the deepest-supported language; JavaScript and HTML get regex/rule-based checks only (Bandit, Pylint, and Radon are Python tools).
- An Anthropic API key is available; the free-tier host can run Bandit/Pylint as subprocesses.
- Code pasted is a single file of up to 50,000 characters.
- No user accounts are required for MVP; identity is an anonymous client ID stored in the browser.

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Pasted code is executed or exploits analyzers | High | Never execute submitted code; run linters in subprocess with timeout, temp dir, no network |
| AI API cost or abuse | Medium | Per-scan cap (default 10 explanations), IP rate limits, cache by finding signature |
| AI hallucinated fixes | Medium | Label fixes as suggestions; keep the rule-based finding as source of truth |
| Free-tier host sleeps / slow cold start | Low | Show loading state; document in README |
| Subprocess tools slow on large input | Medium | Timeouts (20 s per tool), 50k-char cap, parallel execution |
| Non-Python languages have shallow coverage | Medium | State coverage clearly in UI per language |
| Privacy concerns over pasted code | Medium | Do not persist code; store SHA-256 hash only; explain in UI |
| "Recurring mistake" feature infeasible via code hash alone | Medium | Track by `client_id` + pattern type, not code hash (see SRS FR-60 series) |

## 10. Acceptance Criteria (MVP)

1. A user can paste Python code, select Full, and receive a review board with a score, grade, and findings grouped by severity.
2. At least the top 10 Critical/High findings include an AI explanation and fix, or a clear "AI unavailable" note while the rest of the report still renders.
3. Status changes persist after page refresh.
4. Re-submitting modified code shows which prior issues were resolved.
5. A PDF report downloads and contains cover, summary table, findings, and improvement suggestions.
6. The mistake history page shows pattern counts across at least two sessions from the same browser.
7. Empty, oversized, and unsupported-language submissions are rejected with clear messages.
8. The 6th scan within one minute from one IP returns HTTP 429.
9. The database contains no raw submitted code.
10. App is deployed to a public free-tier URL and the local setup works from the README.

## 11. Open Questions

- Should JavaScript support include ESLint via Node, or stay regex-only for MVP? (Recommended: regex-only.)
- Is the Admin role in scope for the lab demo, or only documented? (Recommended: minimal token-protected stats endpoint.)