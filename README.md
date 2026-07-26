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
