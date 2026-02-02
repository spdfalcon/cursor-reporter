#!/usr/bin/env bash
# Run Cursor daily report and save to ~/cursor/reports/
# سپس گزارش خام را به OpenRouter می‌فرستد و گزارش کار کوتاه (با تاریخ شمسی) می‌گیرد.
# Default: today, window 3:00 AM – 1:00 AM next day.
# Usage:
#   ./run_daily_report.sh              # today (خلاصه با OpenRouter، کلید پیش‌فرض)
#   ./run_daily_report.sh 2026-01-30   # that date

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORTS_DIR="${SCRIPT_DIR}/reports"
mkdir -p "$REPORTS_DIR"

DATE="${1:-$(date +%Y-%m-%d)}"
OUTPUT="${REPORTS_DIR}/cursor-report-${DATE}.md"

# ۱) ساخت گزارش خام از چت‌های Cursor
python3 "${SCRIPT_DIR}/cursor_daily_report.py" --date "$DATE" --output "$OUTPUT"
echo ""
echo "Open (raw): $OUTPUT"

# ۲) ارسال به OpenRouter و ذخیرهٔ گزارش کوتاه (کلید پیش‌فرض یا OPENROUTER_API_KEY)
echo ""
python3 "${SCRIPT_DIR}/summary_report.py" "$OUTPUT"
SUMMARY_OUT="${REPORTS_DIR}/summary-report-${DATE}.md"
echo ""
echo "Open (short): $SUMMARY_OUT"
