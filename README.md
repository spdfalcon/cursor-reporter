# Cursor Daily Report

Collects Cursor chats and builds a raw report; then sends it to **Google Gemini API** and saves a **short work summary** (Jalali date and per-project summary). Uses only Python standard library (urllib, json) — no extra packages.

---

## Requirements

- **Linux** (e.g. Ubuntu)
- **Python 3**
- Cursor with Agent/Composer mode (so transcripts are saved under `~/.cursor/projects/`)
- **Gemini API key:** A key is built into the project; no setup needed. To use your own: `export GEMINI_API_KEY='...'`

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
