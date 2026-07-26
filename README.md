# Invoicing challenge

**CONFIDENTIAL CHALLENGE MATERIAL — do not share or post any part of this
package or your solution, ever.** Doing so ends your candidacy and
permanently disqualifies you from all current and future roles with the
hiring company.

## Your brief

You are Gordon, the engineer this work lands on. Your direction comes from
the team's chat: [`chat/billing-recon.md`](chat/billing-recon.md). Read it
top to bottom — what to build and what governs are all in there — then get it done.

The codebase is a small Python invoicing service — standard library only,
nothing to install. Verify your setup and your work with:

```sh
make test-visible
```

## Your clock

Your 180 minutes start when you submit the Start Form and include
everything: reading, agent work, verification, transcript export, packaging,
upload, and the Results Form. Reserve the final 15 minutes for export and
submission.

## Agent transcripts

You may use only these exact surfaces. Submit the required native export of
every session, delegated thread, and subagent you use. Put the records under
`transcripts/native/` and list each in `transcripts/INDEX.md`. Every session
entry must state the exact approved surface, exact model identifier as the
surface reports it, exact reasoning/thinking setting displayed by the surface
(or `not exposed`), purpose, session/thread ID, parent ID when delegated, and
native export path.

Use this exact session table in `INDEX.md`:

| Approved surface | Exact model identifier | Reasoning/thinking setting | Purpose | Session/thread ID | Parent ID | Native export path |
|---|---|---|---|---|---|---|
| Codex CLI | gpt-5.6-sol | xhigh | Example only | session-id | not delegated | transcripts/native/codex/session.jsonl |

| Approved surface | Required export |
|---|---|
| Claude Code CLI | Run `/export transcripts/native/claude/cli-<id>.txt` in every session; also copy the matching raw JSONL and associated `subagents/` records from the normal `~/.claude/projects/` tree. |
| Claude Desktop’s local Code tab | Use only local top-level **Code tab** sessions. Run `/export transcripts/native/claude/desktop-<id>.txt` in every session; also copy the matching raw JSONL and its `subagents/` records from the normal `~/.claude/projects/` tree. Before starting, test that you can identify and export both records; if you cannot, do not use Desktop. |
| Codex CLI | Copy session JSONL files from `${CODEX_HOME:-~/.codex}/sessions/` (including dated subfolders) and relevant archived sessions. For non-interactive work, capture `codex exec --json` through `tee`. Do not use `--ephemeral`. |
| Codex in the ChatGPT desktop app (local) | Copy local session JSONL files from `${CODEX_HOME:-~/.codex}/sessions/` (including dated subfolders) and relevant archived sessions. |
| Cursor’s local IDE Agent | Use the local Agent chat history's Export action and save the native Markdown. |
| Cursor Agent CLI in captured print mode | Use only `--print --output-format stream-json` and capture the complete output through `tee`. |

Claude Desktop ordinary Chat, Cowork, side chats/`/btw`, Dispatch, web,
cloud/remote, and SSH sessions are disallowed. Codex web/cloud and the IDE
extension are disallowed. Cursor Background Agents, inline completion/Tab,
other Cursor AI surfaces, and interactive Agent CLI are disallowed.

**Do a test export before you start**, so you know it works on your machine.
If you discover at the end that you cannot export your transcripts, your
submission will not be reviewed.

Export transcripts unmodified — you may redact secrets, but note every
redaction in `INDEX.md`. Summaries, screenshots, or rewritten logs do not
replace native exports. Native records corroborate the INDEX declaration where
the vendor exposes the relevant metadata; the INDEX is still required because
native formats do not consistently expose every value, especially
reasoning/thinking settings.

## Package and submit

Build this structure and zip it:

```text
submission/
├── repository/          (your working tree, without .git or caches)
├── transcripts/
│   ├── INDEX.md
│   └── native/
└── RELEASE_NOTE.md
```

This package is challenge version `inv-2026.8`.

Exclude `.git`, caches, build output, credentials, and unrelated files. The
ZIP must be at most 100 MB compressed.

Then:

1. Upload the ZIP to a direct download link that needs no login or cookies
   (for example an unlisted cloud-storage link). Keep the file there,
   unchanged and directly downloadable, for seven days after submitting the
   Results Form. The company captures the submitted bytes immediately and
   evaluates the evaluator-owned copy afterward.
2. Download it back from that link and confirm the download's SHA-256 hash
   matches your local ZIP:

```sh
# macOS/Linux
shasum -a 256 submission.zip
curl -fsSL "<your-link>" --output check.zip
shasum -a 256 check.zip   # must match, then delete check.zip
```

```powershell
# Windows PowerShell
Get-FileHash .\submission.zip -Algorithm SHA256
Invoke-WebRequest -Uri "<your-link>" -OutFile .\check.zip
Get-FileHash .\check.zip -Algorithm SHA256   # must match, then delete check.zip
```

3. Put the link and the hash in the Results Form. Do not change or replace
   the uploaded file afterward.

---

# 🚀 Challenge Completion & System Documentation

This repository has been fully completed and upgraded into a production-grade, containerized full-stack solution with a beautiful dashboard and automated CI/CD deployment.

## 🏆 What Was Accomplished

We resolved all correctness bugs, implemented all requested business features, and designed a robust, modern interface to make billing reconciliation simple and intuitive:

### 1. Correctness & Mathematical Integrity (`pricing/engine.py`)
- **Aggregate-then-Allocate Rounding**: Replaced line-by-line rounding with an aggregate-level calculation and allocation algorithm (`allocate`). This guarantees line-item cents sum exactly to the aggregate rounded amount, eliminating cent-rounding discrepancies.
- **Multiplicative Promotions**: Fixed promotion combining to combine multiplicatively per line before allocating the aggregate reduction.
- **Exclusive Promotion Selection**: Programmed the engine to simulate the full pipeline for each exclusive promotion and pick the one that results in the lowest final total, breaking ties by key ascending.

### 2. Robust Adjustments & Runs (`adjustments/intake.py`)
- **Partner Retry/Duplicate Logic**: 
  - Same adjustment ID with identical fields is treated as an idempotent retry.
  - Same adjustment ID with different fields (e.g. amount) replaces the prior payload, triggering a state rebuild.
  - Different adjustment IDs with identical fields within 24 hours are collapsed as retries.
- **Withdrawals (Reversals)**: Programmed reversals to write equal-and-opposite records that sum to zero, ensuring perfect auditability.
- **Immutability of Issued Runs**: Fixed a major bug where deliveries were modifying already issued statement runs and `amount_due`. Issued runs are now completely frozen and immutable.
- **Run Summaries Adoption**: Implemented `adopt_run_summaries(account, adoption_id)` to backfill summaries on historical runs and keep them synchronized with the current position of their invoices.

### 3. Statement Screen Redesign ("Calm Bill") (`statement/view.py`)
- Redesigned the statement screen to show a clean, high-level summary (Original invoice total, Settled corrections, Pending corrections, and Final amount due) while collapsing detailed correction histories by default.
- Ensured all key facts are readable from visible nodes without expanding any collapsed node, fulfilling accessibility rules.
- Presented inline run summaries as first-class nodes, expanded by default on all viewports.
- Added a beautifully styled HTML output with a billing department fax number and Roman numeral page numbering footer.

---

## 🛠️ Overview of the Tech Stack & Setup

The project has been scaled from a simple Python command-line utility into a modern multi-tier web application:

```text
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                       │
│  (Interactive Dashboard, Calm Bill Render, Forms, Runs) │
└────────────────────────────┬────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────┐
│                    Django Backend                       │
│   (API Routes, In-Memory Models, Session Persistence)   │
└────────────────────────────┬────────────────────────────┘
                             │ Imports
┌────────────────────────────▼────────────────────────────┐
│             Core Invoicing & Pricing Engine             │
└─────────────────────────────────────────────────────────┘
```

1. **Django API Backend**: Exposes clean, RESTful endpoints at `/api/` to query ledger state, deliver adjustments, run statement runs, and fetch statements.
2. **React Frontend Dashboard**: A beautiful, single-page React app served directly from the root path `/` of our Django server. It contains live account statistics, interactive form submissions, statement runs history, and phone/tablet mock statement screens.
3. **Containerization**: Configured with a `Dockerfile` and `docker-compose.yml` to build and run the entire stack with a single command under the container name `billing-challenge-friendi-fi`.

---

## 🔧 Tools & Libraries Used

- **Python 3.11** (Standard Library, Decimal, Datetime, Unittest) — Used for core pricing and adjustments logic.
- **Django 4.2** & **Django CORS Headers** — Exposes REST API endpoints and serves the static frontend.
- **React 18** — Powers the interactive, single-page dashboard.
- **Tailwind CSS** — Provides modern, responsive styling.
- **Lucide Icons** — Renders beautiful vector icons on the dashboard.
- **Docker** & **Docker Compose** — Orchestrates and containerizes the backend/frontend services under the explicit container name `billing-challenge-friendi-fi`.
- **Git** & **GitHub Actions** — Handles version control and automates the build and deployment of the frontend to **GitHub Pages** on every push to the `main` branch.
