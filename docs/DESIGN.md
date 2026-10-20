# UI/UX Document: CodeReview AI

**Version:** 1.0 | **Design goals:** simple, modern, encouraging (teacher tone, not scolding), usable on a phone or a lab PC.

---

## 1. Design Principles

1. **One obvious action per screen.** Paste, review, fix.
2. **Teach, don't shame.** Wording is constructive ("Here's how to improve this").
3. **Worst first.** Severity drives order and colour.
4. **Never colour alone.** Every severity has an icon and a text label.
5. **Fast feedback.** Show progress during scans; never a blank screen.
6. **Privacy visible.** State plainly that the code is not stored.

## 2. User Journey

| Stage | User action | System response | Emotion goal |
|---|---|---|---|
| Arrive | Opens home page | Large editor, clear headline | Confident |
| Submit | Pastes code, picks language and mode | Button enables, scan starts, stepper shows progress | Reassured |
| Wait | Watches progress | Steps tick: Analyzing, Checking security, Explaining | Patient |
| Review | Lands on review board | Score ring, severity summary, cards | Informed |
| Fix | Reads explanation, copies fix | Copy button confirms | Empowered |
| Track | Changes status | Instant save with toast | In control |
| Re-scan | Pastes revised code | Comparison banner: "4 fixed, 1 new" | Motivated |
| Export / reflect | Downloads PDF, opens history | PDF downloads; top-mistakes list | Progress |

## 3. Navigation and Sitemap

```
Top bar: [Logo CodeReview AI]   New Review | My Reviews | My Mistakes | (Admin)
 ├─ index.html     New Review (home)
 ├─ review.html    Review Board  (?session=<id>)
 ├─ report.html    Report view / print-friendly  (?session=<id>)
 ├─ history.html   My Mistakes + past sessions   (add to folder structure)
 └─ admin.html     Analytics (token gated, optional)
```
- Mobile: top bar collapses to a hamburger menu.
- Breadcrumb on review and report: `My Reviews > Session 12 Oct, 14:32`.

## 4. Screens

### 4.1 Home / New Review (`index.html`)
Layout (top to bottom):
1. **Hero line:** "Paste your code. Get a teacher-style review." Sub-line: "No sign-up. We don't store your code."
2. **Controls row:** Language select (Python / JavaScript / HTML) | Review type segmented control (Quick / Full / Security-only) with a one-line description under the selected option.
3. **Code editor:** monospace textarea, min 14 rows, line-count and character counter (`1,240 / 50,000`), "Clear" and "Paste from clipboard" buttons.
4. **Collapsible "Add requirements.txt (optional)"** panel, shown for Python only.
5. **Primary button:** "Review my code" (full width on mobile). Disabled until code is at least 10 characters.
6. **Re-scan mode:** when arriving from a review with "Re-submit fixed code", a banner reads "Re-scanning: compare with Session 12 Oct" and the language is locked.

### 4.2 Scanning State
Overlay card with a vertical stepper:
`Validating` > `Running security checks` > `Checking quality & bugs` > `Writing explanations` > `Saving`.
Indeterminate bar, plus "Usually takes 10-30 seconds". Cancel button aborts the fetch.

### 4.3 Review Board (`review.html`)
- **Header strip:** score ring (0-100, colour by grade), grade letter, summary chips (`1 Critical`, `3 High`, `4 Medium`, `2 Low`), scan meta (language, mode, time).
- **Actions:** `Download PDF`, `Re-submit fixed code`, `New review`.
- **Filter bar:** severity chips (toggle), category select, status select, and a text search.
- **Progress bar:** "3 of 10 issues resolved".
- **Findings list:** cards grouped under sticky severity headings.
- **Comparison banner** (if re-scan): "Resolved 4 | Still open 3 | New 1".
- **AI notice** (if unavailable): "AI explanations are unavailable right now; showing rule-based advice."

**Finding card anatomy**
```
[● Critical]  Use of eval()                       Line 12      [Status ▾]
Category: Security
What's wrong (AI explanation, 3 sentences)
Why it matters / description (rule text, collapsed on mobile)
Suggested fix
 ┌───────────────────────────────────────────┐
 │ code block with syntax highlighting  [Copy]│
 └───────────────────────────────────────────┘
```
- Cards are collapsed by default except Critical and High; click header to toggle.
- Status dropdown: Open, Acknowledged, In progress, Fixed, Ignored; saves immediately, showing a small spinner then "Saved".
- Ignored cards dim and move to the bottom of their group.

### 4.4 Report (`report.html`)
Print-optimised view mirroring the PDF: cover summary, table of counts, findings by severity, improvement suggestions. `Download PDF` and `Print` buttons.

### 4.5 My Mistakes (`history.html`)
- Horizontal bar chart of top 5 recurring patterns (count).
- For each: plain-English tip and "Seen in N scans, last on <date>".
- Below: past sessions table (date, language, mode, score, grade, open issues) linking to the review board.
- Empty state: "Run your first review to start tracking your habits."

### 4.6 Admin (optional)
Token prompt, then cards: scans per day, grade distribution, top categories, rules table with toggles.

## 5. Components

| Component | Variants / notes |
|---|---|
| Button | Primary (filled), Secondary (outline), Ghost; sizes M/L; loading and disabled states |
| Segmented control | Review type; keyboard arrow navigation |
| Select | Language, status, filters |
| Textarea / code editor | Monospace, counter, error outline |
| Score ring | SVG circle; colour by grade; animated fill 600 ms (respect reduced motion) |
| Severity badge | Icon + label: Critical (octagon), High (triangle), Medium (circle-exclamation), Low (info) |
| Finding card | Collapsed / expanded / ignored |
| Code block | Copy button, horizontal scroll |
| Toast | Success, error; auto-dismiss 4 s; `aria-live="polite"` |
| Banner | Info, warning (AI unavailable), success (comparison) |
| Stepper | Scan progress |
| Modal | Re-submit confirmation, error details |
| Skeleton | Placeholder cards while loading |

## 6. Forms and Validation

| Field | Rule | Message |
|---|---|---|
| Code | Required, 10-50,000 chars, not whitespace-only | "Paste at least a few lines of code." / "That's over the 50,000 character limit; try a smaller file." |
| Language | One of three | Preselected, cannot be empty |
| Review type | One of three | Preselected: Full |
| Requirements | Optional, max 10,000 chars | "requirements.txt is too long." |

Validation runs on input (counter) and on submit; errors show inline under the field, linked with `aria-describedby`, and focus moves to the first error.

## 7. States

| Screen | Loading | Empty | Error |
|---|---|---|---|
| Home | n/a | Placeholder text in editor | Inline field errors; server 422 messages mapped to fields |
| Scan | Stepper | n/a | "Something went wrong. Your code wasn't saved. Try again." with Retry |
| Rate limited (429) | n/a | n/a | "You're going a bit fast. Try again in {n} seconds." with countdown |
| Review board | Skeleton ring + 4 skeleton cards | **No issues:** "Clean scan! Score 100." with a celebratory icon | "We couldn't load this review." Retry / Back |
| Session not found | n/a | n/a | "This review doesn't exist or belongs to another browser." |
| History | Skeleton rows | "No history yet" | Retry |
| Status change | Spinner in dropdown | n/a | Revert the dropdown, toast "Couldn't save. Try again." |
| PDF | Button spinner | n/a | Toast with the reason (429: "PDF limit reached; try later") |

## 8. Responsive Behavior

| Breakpoint | Behavior |
|---|---|
| < 640 px (mobile) | Single column; controls stack; score ring above chips; filter bar becomes a "Filters" bottom sheet; cards fully collapsed except title and badge; sticky "Review my code" button |
| 640-1023 px (tablet) | Two-column header; cards full width |
| >= 1024 px (desktop) | Max content width 1100 px; left column (score, filters) sticky, right column findings |

Touch targets are at least 44x44 px. Editor font stays 14 px or larger to prevent iOS zoom.

## 9. Accessibility (WCAG 2.1 AA)

- Contrast >= 4.5:1 for text, >= 3:1 for UI components in both themes.
- Logical heading order (`h1` per page); landmarks (`header`, `nav`, `main`).
- All controls keyboard operable; visible 2 px focus ring; skip-to-content link.
- Dropdown/toggle labels via `<label>` or `aria-label`; cards use `<details>`/`aria-expanded`.
- Severity conveyed by icon and text, not colour alone.
- Score ring has `role="img"` with `aria-label="Score 62 out of 100, grade C"`.
- Toasts use `aria-live`; scan progress uses `role="status"`.
- Respect `prefers-reduced-motion` and `prefers-color-scheme`.
- Code blocks are focusable for keyboard scrolling.

## 10. Visual Design System

### 10.1 Typography
| Role | Font | Size / weight |
|---|---|---|
| UI | Inter (fallback: system-ui, sans-serif) | Body 16 px / 400; labels 14 px / 500 |
| Code | JetBrains Mono (fallback: ui-monospace, Menlo, Consolas) | 14 px / 400 |
| H1 | Inter | 32 px / 700 (24 px mobile) |
| H2 | Inter | 24 px / 600 |
| H3 | Inter | 18 px / 600 |

### 10.2 Colour Tokens
| Token | Light | Dark |
|---|---|---|
| `--bg` | #FFFFFF | #0F172A |
| `--surface` | #F8FAFC | #1E293B |
| `--border` | #E2E8F0 | #334155 |
| `--text` | #0F172A | #F1F5F9 |
| `--text-muted` | #475569 | #94A3B8 |
| `--primary` | #4F46E5 | #818CF8 |
| `--critical` | #B91C1C | #F87171 |
| `--high` | #C2410C | #FB923C |
| `--medium` | #A16207 | #FACC15 |
| `--low` | #15803D | #4ADE80 |
| Code bg | #0F172A | #020617 |

Grade colours: A green, B teal, C amber, F red (always paired with the letter).

### 10.3 Spacing and Shape
- 4 px base scale: 4, 8, 12, 16, 24, 32, 48.
- Card padding 16 px (24 px desktop); gap between cards 12 px.
- Radius: 8 px controls, 12 px cards; 1 px borders; one soft shadow for elevated modals only.

### 10.4 Iconography and Motion
- Lucide-style outline icons, 20 px.
- Transitions 150-200 ms ease-out; score ring 600 ms; all disabled under reduced motion.

## 11. Content and Tone

- Buttons use verbs: "Review my code", "Copy fix", "Re-submit fixed code".
- Errors say what happened and what to do next; no jargon, no blame.
- Empty states are encouraging.
- Privacy line under the editor: "Your code is analyzed and discarded. We keep only the findings."

## 12. Implementation Notes

- Build one shared `style.css` with the tokens above as CSS variables, and load Tailwind (compiled output preferred over CDN to satisfy the CSP).
- Put all JS in `app.js` (home) and `review.js` (board), plus `history.js`; avoid inline scripts and inline event handlers.
- Render server data with `textContent` or an escape helper.
- Persist client ID in `localStorage` key `cr_client_id`; theme preference in `cr_theme`.