#!/usr/bin/env python3
"""
Send Cursor daily raw report to Google Gemini API and save a short work summary
(with Jalali date). Uses only standard library (urllib, json) — no extra packages.

Usage:
  python3 summary_report.py                    # today's report
  python3 summary_report.py reports/cursor-report-2026-02-01.md

Output: reports/summary-report-YYYY-MM-DD.md
Built-in API key is used by default; override with GEMINI_API_KEY or --api-key.
"""

import argparse
import json
import os
import sys
from pathlib import Path
import urllib.request
import urllib.error


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_API_KEY = "AIzaSyCbv5_wcJ83ta5xGoOvKpmBiUT14MDHyyI"
REQUEST_TIMEOUT = 120
MAX_RETRIES = 3


def load_report(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_prompt(report_content: str, date_gregorian: str) -> str:
    return f"""این متن یک گزارش خام از تمام چت‌های Cursor در تاریخ {date_gregorian} است (با جزئیات هر پروژه و هر مکالمه).

وظیفهٔ تو:
از روی این گزارش، یک **گزارش کار روزانه** خیلی کوتاه و تمیز به فارسی بنویس با این شرایط:
1. در همان اول گزارش، **تاریخ امروز را به شمسی (جلالی)** بنویس.
2. برای **همهٔ پروژه‌ها** که در گزارش خام هستند (هر بخشی که با ## شروع شده یک پروژه است) حتماً یک بخش جداگانه بنویس؛ هیچ پروژه‌ای را حذف نکن. برای هر پروژه یک یا دو خط خلاصه بنویس که آن روز چه کاری انجام شده، بدون اصطلاحات فنی زیاد.
3. **اسم فایل‌هایی که ویرایش یا ساخته شده** را هم بنویس (مثلاً نام فایل‌های .py، .html، .sh و غیره).
4. گزارش باید **خیلی کوتاه** باشد؛ فقط خلاصهٔ کارها، نه تکرار کل چت‌ها.
5. از کلمات ساده و قابل فهم استفاده کن، نه اصطلاحات تخصصی.

فقط خروجی نهایی گزارش را بنویس، بدون توضیح اضافه یا «بله، گزارش به این شکل است» و امثال آن.

---
متن گزارش خام:
---
{report_content}
"""


def _request_one(api_key: str, prompt: str, model: str) -> str:
    url = f"{GEMINI_BASE}/{model}:generateContent?key={api_key}"
    body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 8192,
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    try:
        text = out["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError("Invalid Gemini response: " + json.dumps(out, ensure_ascii=False)[:400]) from e
    if not (text and str(text).strip()):
        raise ValueError("Gemini returned empty text.")
    return str(text).strip()


def call_gemini(api_key: str, prompt: str, model: str | None = None) -> str:
    current_model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"  Retry ({attempt}/{MAX_RETRIES})...")
            return _request_one(api_key, prompt, current_model)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if attempt < MAX_RETRIES and e.code in (429, 503):
                continue
            raise SystemExit(f"Gemini API error (HTTP {e.code}): {err_body}")
        except urllib.error.URLError as e:
            if "timed out" in str(e.reason).lower() or "timeout" in str(e.reason).lower():
                if attempt < MAX_RETRIES:
                    continue
            raise SystemExit(f"Connection error: {e.reason}")
        except ValueError as e:
            raise SystemExit(str(e))
    raise SystemExit("Request failed after retries.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send Cursor raw report to Gemini and save short work summary."
    )
    parser.add_argument(
        "report_file",
        nargs="?",
        default=None,
        help="Path to raw report. Default: today's report.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY") or DEFAULT_API_KEY,
        help="Gemini API key (default: built-in key in project).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: reports/summary-report-YYYY-MM-DD.md).",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL,
        help=f"Gemini model (default: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    reports_dir = script_dir / "reports"

    if args.report_file:
        report_path = Path(args.report_file)
        if not report_path.is_absolute():
            report_path = (script_dir / report_path).resolve()
    else:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        report_path = reports_dir / f"cursor-report-{today}.md"

    if not report_path.exists():
        print(f"Report file not found: {report_path}", file=sys.stderr)
        sys.exit(1)

    date_gregorian = (
        report_path.stem.replace("cursor-report-", "")
        if "cursor-report-" in report_path.name
        else "today"
    )
    report_content = load_report(report_path)
    prompt = build_prompt(report_content, date_gregorian)

    print("Sending to Gemini...")
    summary = call_gemini(args.api_key, prompt, model=args.model)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = reports_dir / f"summary-report-{date_gregorian}.md"
    if not out_path.is_absolute():
        out_path = (script_dir / out_path).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(summary, encoding="utf-8")
    print(f"Summary saved: {out_path}")
    print("")
    print("---")
    print(summary[:800] + ("..." if len(summary) > 800 else ""))


if __name__ == "__main__":
    main()
