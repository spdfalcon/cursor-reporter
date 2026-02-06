# Cursor Daily Report

Collects Cursor chats and builds a raw report; then sends it to **Google Gemini API** and saves a **short work summary** (Jalali date and per-project summary). Uses only Python standard library (urllib, json) — no extra packages.

---

## Requirements

- **OS:** Linux, macOS, or Windows (Cursor paths are detected per OS)
- **Python 3**
- Cursor with Agent/Composer mode (transcripts under `~/.cursor/projects/<project>/agent-transcripts/`)
- **Gemini API key:** Put `GEMINI_API_KEY=...` in project `.env`, or set in environment / `--api-key`

---

## Usage

### Today’s report

```bash
cd ~/cursor
chmod +x run_daily_report.sh
./run_daily_report.sh
```

Output:
- `reports/cursor-report-YYYY-MM-DD.md` — raw report (work summary only, compact)
- `reports/summary-report-YYYY-MM-DD.md` — short work report from Gemini (Jalali date, plain language)

### Report for a specific date

```bash
./run_daily_report.sh 2026-02-01
```

---

## Files

| File | Role |
|------|------|
| `run_daily_report.sh` | Main script: raw report + Gemini short report |
| `cursor_daily_report.py` | Builds raw report from Cursor transcripts (window: 3 AM – 1 AM next day) |
| `summary_report.py` | Sends raw report to Gemini API (REST, urllib only) and saves the short report |

---

## Optional

- **Gemini API key:** Built-in by default. Override with `export GEMINI_API_KEY='...'` or `--api-key=...`
- **Gemini model:** `export GEMINI_MODEL=gemini-2.5-pro` (default: `gemini-2.5-flash`)
- **Short report only from an existing file:**  
  `python3 summary_report.py reports/cursor-report-2026-02-01.md`

Reference: [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/quickstart)

---

## How it finds Cursor data (multi-OS)

- **Agent transcripts:** `~/.cursor/projects/<project>/agent-transcripts/*.txt` (same path on Linux, macOS, Windows).
- **Workspace paths** (to show real project folder paths) are read from Cursor’s workspace storage:
  - **Linux:** `~/.config/Cursor/User/workspaceStorage/*/workspace.json`
  - **macOS:** `~/Library/Application Support/Cursor/User/workspaceStorage/*/workspace.json`
  - **Windows:** `%APPDATA%\Cursor\User\workspaceStorage\*\workspace.json`

If a project is not in workspace storage, the script falls back to a path derived from the project slug (e.g. `home-user-foo` → `/home/user/foo` on Linux).
