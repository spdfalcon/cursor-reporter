#!/usr/bin/env python3
"""
گزارش روزانهٔ Cursor را به OpenRouter می‌فرستد و یک گزارش کار کوتاه (با تاریخ شمسی)
برمی‌گرداند و ذخیره می‌کند.

فقط از مدل openai/gpt-oss-120b:free (رایگان) استفاده می‌شود.

استفاده:
  python3 summary_report.py              # گزارش امروز
  python3 summary_report.py reports/cursor-report-2026-02-01.md

خروجی: reports/summary-report-YYYY-MM-DD.md
"""

import argparse
import json
import os
import sys
from pathlib import Path
import urllib.request
import urllib.error

# فقط این مدل (رایگان)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b:free"
REQUEST_TIMEOUT = 180  # ثانیه
MAX_RETRIES = 3
# اگر OPENROUTER_API_KEY ست نکردی، این کلید استفاده می‌شود
DEFAULT_API_KEY = "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"


def load_report(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_prompt(report_content: str, date_gregorian: str) -> str:
    return f"""این متن یک گزارش خام از تمام چت‌های Cursor در تاریخ {date_gregorian} است (با جزئیات هر پروژه و هر مکالمه).

وظیفهٔ تو:
از روی این گزارش، یک **گزارش کار روزانه** خیلی کوتاه و تمیز به فارسی بنویس با این شرایط:
1. در همان اول گزارش، **تاریخ امروز را به شمسی (جلالی)** بنویس.
2. برای **هر پروژه** (هر بخش/پوشهٔ کاری) یک خط یا دو خط خلاصه بنویس که آن روز چه کاری انجام شده، بدون اصطلاحات فنی زیاد.
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
    """یک درخواست با مدل مشخص؛ در صورت خطا exception می‌اندازد."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    try:
        text = out.get("choices", [{}])[0].get("message", {}).get("content", "")
    except (IndexError, KeyError):
        raise ValueError("پاسخی از OpenRouter دریافت نشد: " + json.dumps(out, ensure_ascii=False)[:300])
    if not (text and text.strip()):
        raise ValueError("متن خروجی خالی بود.")
    return text.strip()


def call_openrouter(api_key: str, prompt: str, model: str | None = None) -> str:
    """فقط با مدل openai/gpt-oss-120b:free درخواست می‌زند (با رتری برای timeout)."""
    current_model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"  تلاش مجدد ({attempt}/{MAX_RETRIES})...")
            return _request_one(api_key, prompt, current_model)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"خطای OpenRouter (HTTP {e.code}): {err_body}")
        except urllib.error.URLError as e:
            if "timed out" in str(e.reason).lower() or "timeout" in str(e.reason).lower():
                if attempt < MAX_RETRIES:
                    print(f"  زمان درخواست تمام شد؛ تلاش مجدد ({attempt}/{MAX_RETRIES})...")
                    continue
            raise SystemExit(f"خطای اتصال به OpenRouter: {e.reason}")
        except ValueError as e:
            raise SystemExit(str(e))

    raise SystemExit("درخواست بعد از چند تلاش ناموفق بود.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ارسال گزارش Cursor به OpenRouter و دریافت گزارش کار کوتاه")
    parser.add_argument(
        "report_file",
        nargs="?",
        default=None,
        help="مسیر فایل گزارش خام. اگر ندهی، گزارش امروز استفاده می‌شود.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENROUTER_API_KEY") or DEFAULT_API_KEY,
        help="کلید API OpenRouter (پیش‌فرض: env OPENROUTER_API_KEY یا کلید داخلی)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="مسیر ذخیرهٔ گزارش نهایی (پیش‌فرض: reports/summary-report-YYYY-MM-DD.md)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL,
        help=f"مدل OpenRouter (پیش‌فرض: {DEFAULT_MODEL})",
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
        print("کلید OpenRouter را تنظیم کن: export OPENROUTER_API_KEY='...' یا --api-key=...", file=sys.stderr)
        sys.exit(1)

    date_gregorian = report_path.stem.replace("cursor-report-", "") if "cursor-report-" in report_path.name else "امروز"
    report_content = load_report(report_path)
    prompt = build_prompt(report_content, date_gregorian)

    print("در حال ارسال به OpenRouter...")
    summary = call_openrouter(args.api_key, prompt, model=args.model)

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = reports_dir / f"summary-report-{date_gregorian}.md"
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
