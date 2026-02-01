# Cursor Daily Report

Collects Cursor chats and builds a raw report; with a Gemini API key you also get a **short work summary** (Jalali date and per-project summary).

---

## Requirements

- **Linux** (e.g. Ubuntu)
- **Python 3**
- Cursor with Agent/Composer mode (so transcripts are saved under `~/.cursor/projects/`)
- For the short report: **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey)

---

## Usage

### Today’s report

```bash
cd ~/cursor-reporter
chmod +x run_daily_report.sh
./run_daily_report.sh
```git 

Output:
- `reports/cursor-report-YYYY-MM-DD.md` — raw report (all chats and details)

### Short report via Gemini

```bash
export GEMINI_API_KEY='your-api-key'
./run_daily_report.sh
```

Additional output:
- `reports/gemini-report-YYYY-MM-DD.md` — short work report, Jalali date, per-project summary, plain language

### Report for a specific date

```bash
./run_daily_report.sh 2026-02-01
```

---

## Files

| File | Role |
|------|------|
| `run_daily_report.sh` | Main script: raw report + Gemini short report when key is set |
| `cursor_daily_report.py` | Builds raw report from Cursor transcripts (window: 3 AM – 1 AM next day) |
| `gemini_summary_report.py` | Sends raw report to Gemini and saves the short report |

---

## Optional

- **Gemini model:** `export GEMINI_MODEL=gemini-2.0-flash` (default: `gemini-2.5-flash`)
- **Short report only from an existing file:**  
  `python3 gemini_summary_report.py reports/cursor-report-2026-02-01.md`
