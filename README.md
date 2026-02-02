# Cursor Daily Report

Collects Cursor chats and builds a raw report; then sends it to **OpenRouter** and saves a **short work summary** (Jalali date and per-project summary). No extra setup needed — uses a built-in API key by default.

---

## Requirements

- **Linux** (e.g. Ubuntu)
- **Python 3**
- Cursor with Agent/Composer mode (so transcripts are saved under `~/.cursor/projects/`)

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
- `reports/summary-report-YYYY-MM-DD.md` — short work report from OpenRouter (Jalali date, plain language)

### Report for a specific date

```bash
./run_daily_report.sh 2026-02-01
```

---

## Files

| File | Role |
|------|------|
| `run_daily_report.sh` | Main script: raw report + OpenRouter short report |
| `cursor_daily_report.py` | Builds raw report from Cursor transcripts (window: 3 AM – 1 AM next day) |
| `summary_report.py` | Sends raw report to OpenRouter and saves the short report |

---

## Optional

- **OpenRouter API key:** By default a built-in key is used. To use your own: `export OPENROUTER_API_KEY='your-key'`
- **OpenRouter model:** `export OPENROUTER_MODEL=google/gemini-2.0-flash-001` (default)
- **Short report only from an existing file:**  
  `python3 summary_report.py reports/cursor-report-2026-02-01.md`

Reference: [OpenRouter Quickstart](https://openrouter.ai/docs/quickstart)
