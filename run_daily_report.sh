#!/usr/bin/env bash
# Run Cursor daily report and save to ~/cursor/reports/
# Then send raw report to Gemini and save short work summary (Jalali date).
# Default: today, window 3:00 AM – 1:00 AM next day.
# Usage:
#   ./run_daily_report.sh               # today
#   ./run_daily_report.sh 2026-01-30    # that date

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORTS_DIR="${SCRIPT_DIR}/reports"
mkdir -p "$REPORTS_DIR"

DATE="${1:-$(date +%Y-%m-%d)}"
OUTPUT="${REPORTS_DIR}/cursor-report-${DATE}.md"

# 1) Build raw report from Cursor transcripts
python3 "${SCRIPT_DIR}/cursor_daily_report.py" --date "$DATE" --output "$OUTPUT"
echo ""
echo "Open (raw): $OUTPUT"

# 2) Send to Gemini and save short report (uses built-in API key)
echo ""
python3 "${SCRIPT_DIR}/summary_report.py" "$OUTPUT"
SUMMARY_OUT="${REPORTS_DIR}/summary-report-${DATE}.md"
echo ""
echo "Open (short): $SUMMARY_OUT"
