#!/usr/bin/env python3
"""
گزارش روزانهٔ Cursor را به Gemini می‌فرستد و یک گزارش کار کوتاه و تمیز (با تاریخ شمسی)
برمی‌گرداند و ذخیره می‌کند.

استفاده:
  export GEMINI_API_KEY="your-key"
  python3 gemini_summary_report.py گزارش-امروز.md
  python3 gemini_summary_report.py  # اگر ندهی، خودش گزارش امروز را پیدا می‌کند

خروجی در همان پوشهٔ reports با نام gemini-report-YYYY-MM-DD.md
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# مدل پیش‌فرض؛ با GEMINI_MODEL می‌توانی عوضش کنی (مثلاً gemini-2.0-flash)
DEFAULT_MODEL = "gemini-2.5-flash"


def load_report(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_prompt(report_content: str, date_gregorian: str) -> str:
    return f"""این متن یک گزارش خام از تمام چت‌های Cursor در تاریخ {date_gregorian} است (با جزئیات هر پروژه و هر مکالمه).

وظیفهٔ تو:
از روی این گزارش، یک **گزارش کار روزانه** خیلی کوتاه و تمیز به فارسی بنویس با این شرایط:
1. در همان اول گزارش، **تاریخ امروز را به شمسی (جلالی)** بنویس.
2. برای **هر پروژه** (هر بخش/پوشهٔ کاری) یک خط یا دو خط خلاصه بنویس که آن روز چه کاری انجام شده، بدون اصطلاحات فنی زیاد.
3. گزارش باید **خیلی کوتاه** باشد؛ فقط خلاصهٔ کارها، نه تکرار کل چت‌ها.
4. از کلمات ساده و قابل فهم استفاده کن، نه اصطلاحات تخصصی.

فقط خروجی نهایی گزارش را بنویس، بدون توضیح اضافه یا «بله، گزارش به این شکل است» و امثال آن.

---
متن گزارش خام:
---
{report_content}
"""


def call_gemini(api_key: str, prompt: str, model: str | None = None) -> str:
    model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        },
    }
    req = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"خطای API جمنای (HTTP {e.code}): {body}")
    except URLError as e:
        raise SystemExit(f"خطای اتصال به جمنای: {e.reason}")

    try:
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
    except (IndexError, KeyError):
        raise SystemExit("پاسخی از جمنای دریافت نشد. پاسخ خام: " + json.dumps(data, ensure_ascii=False)[:500])

    if not text:
        raise SystemExit("متن خروجی از جمنای خالی بود.")
    return text.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="ارسال گزارش Cursor به جمنای و دریافت گزارش کار کوتاه")
    parser.add_argument(
        "report_file",
        nargs="?",
        default=None,
        help="مسیر فایل گزارش خام (مثلاً reports/cursor-report-2026-02-01.md). اگر ندهی، گزارش امروز استفاده می‌شود.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="کلید API جمنای (یا از env: GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="مسیر ذخیرهٔ گزارش نهایی (پیش‌فرض: reports/gemini-report-YYYY-MM-DD.md)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL,
        help="نام مدل جمنای (پیش‌فرض: gemini-2.5-flash؛ یا env GEMINI_MODEL)",
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
        print(f"فایل گزارش پیدا نشد: {report_path}", file=sys.stderr)
        sys.exit(1)

    if not args.api_key:
        print("کلید API جمنای را تنظیم کن: export GEMINI_API_KEY='...' یا --api-key=...", file=sys.stderr)
        sys.exit(1)

    date_gregorian = report_path.stem.replace("cursor-report-", "") if "cursor-report-" in report_path.name else "امروز"
    report_content = load_report(report_path)
    prompt = build_prompt(report_content, date_gregorian)

    print("در حال ارسال به جمنای...")
    summary = call_gemini(args.api_key, prompt, model=args.model)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = reports_dir / f"gemini-report-{date_gregorian}.md"
    if not out_path.is_absolute():
        out_path = (script_dir / out_path).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(summary, encoding="utf-8")
    print(f"گزارش کوتاه ذخیره شد: {out_path}")
    print("")
    print("---")
    print(summary[:800] + ("..." if len(summary) > 800 else ""))


if __name__ == "__main__":
    main()
