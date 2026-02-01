#!/usr/bin/env bash
# Run Cursor daily report and save to ~/cursor/reports/
# سپس گزارش خام را به جمنای می‌فرستد و گزارش کار کوتاه (با تاریخ شمسی) می‌گیرد.
# Default: today, window 3:00 AM – 1:00 AM next day.
# Usage:
#   export GEMINI_API_KEY='your-key'   # برای دریافت گزارش کوتاه از جمنای
#   ./run_daily_report.sh              # today
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

# ۲) ارسال به جمنای و ذخیرهٔ گزارش کوتاه (اگر GEMINI_API_KEY تنظیم شده باشد)
if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  echo ""
  python3 "${SCRIPT_DIR}/gemini_summary_report.py" "$OUTPUT"
  GEMINI_OUT="${REPORTS_DIR}/gemini-report-${DATE}.md"
  echo ""
  echo "Open (short): $GEMINI_OUT"
else
  echo ""
  echo "برای دریافت گزارش کوتاه از جمنای: export GEMINI_API_KEY='your-api-key'"
fi
