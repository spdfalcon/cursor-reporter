#!/usr/bin/env python3
"""
Cursor Daily Work Report Generator.

Reads Cursor agent transcripts from ~/.cursor/projects/*/agent-transcripts/
and builds a report of what you did per project in a configurable time window
(e.g. from 3:00 AM to 1:00 AM next day).

Usage:
  python cursor_daily_report.py                    # report for "today" (3 AM - 1 AM)
  python cursor_daily_report.py --date 2026-01-30 # report for that day
  python cursor_daily_report.py --start 0 --end 24 # full calendar day
"""

import argparse
import os
import re
from datetime import datetime, timedelta
from pathlib import Path


CURSOR_PROJECTS = Path.home() / ".cursor" / "projects"
CURSOR_WS_STORAGE = Path.home() / ".config" / "Cursor" / "User" / "workspaceStorage"


def slug_to_path(slug: str) -> str:
    """Convert project slug to absolute path (e.g. home-mohammadreza-cursor -> /home/mohammadreza/cursor)."""
    return "/" + slug.replace("-", "/")


def path_to_display_name(slug: str) -> str:
    """Short display name from slug (e.g. home-mohammadreza-work-aloroll -> aloroll)."""
    return slug.split("-")[-1] if "-" in slug else slug


def get_workspace_paths() -> dict[str, str]:
    """Build slug -> folder path from workspaceStorage workspace.json files."""
    out = {}
    if not CURSOR_WS_STORAGE.exists():
        return out
    for ws_dir in CURSOR_WS_STORAGE.iterdir():
        if not ws_dir.is_dir():
            continue
        wj = ws_dir / "workspace.json"
        if not wj.exists():
            continue
        try:
            raw = wj.read_text()
            m = re.search(r'"folder"\s*:\s*"file://([^"]+)"', raw)
            if m:
                path = m.group(1).rstrip("/")
                slug = path.strip("/").replace("/", "-")
                out[slug] = path
        except Exception:
            pass
    return out


def parse_transcript(content: str) -> list[str]:
    """Extract user messages (each block after 'user:' until next 'assistant:' or end)."""
    messages = []
    pattern = re.compile(
        r"user:\s*\n\s*<user_query>\s*\n(.*?)(?=\n\s*assistant:|\n\s*user:\s*\n|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(content):
        msg = m.group(1).strip()
        msg = re.sub(r"\s*</user_query>\s*$", "", msg, flags=re.I)
        if msg:
            messages.append(msg)
    if not messages:
        fallback = re.split(r"\n\s*assistant:\s*\n", content, maxsplit=1)[0]
        user_part = re.sub(r"^user:\s*\n", "", fallback, flags=re.I).strip()
        if user_part:
            messages.append(user_part)
    return messages


def parse_transcript_full(content: str) -> list[tuple[str, str]]:
    """
    Parse full transcript into list of (role, content) turns.
    User turns can start with "user:\n" (then optional <attached_files>, then <user_query>)
    OR with "\n<user_query>" only (Cursor sometimes omits "user:\n" for later turns).
    """
    turns: list[tuple[str, str]] = []
    pos = 0

    while pos < len(content):
        # Next user turn: either "\nuser:\n" or "\n<user_query>" (or "user:\n" at start)
        at_start = pos == 0
        find_user_line = content.find("user:\n", pos)
        if at_start and content.startswith("user:\n"):
            find_user_line = 0
        find_query_tag = content.find("\n<user_query>", pos)
        # Pick earliest valid start
        next_user_line = find_user_line if find_user_line != -1 else len(content)
        next_query_tag = find_query_tag if find_query_tag != -1 else len(content)
        if at_start and find_user_line == 0:
            turn_start = 0
            use_query_only = False
        elif next_user_line <= next_query_tag:
            if next_user_line >= len(content):
                break
            allowed = (next_user_line == 0 or
                       "assistant:" in content[max(0, next_user_line - 30) : next_user_line])
            if not allowed:
                pos = next_user_line + 1
                continue
            turn_start = next_user_line + 1  # after "\n", so at "user"
            use_query_only = False
        else:
            turn_start = next_query_tag + 2  # after "\n<", so at "user_query>"
            use_query_only = True

        if use_query_only:
            q_open = turn_start - 1  # "\n<user_query>": "<" at turn_start-1
            q_content_start = content.find("\n", q_open) + 1
            q_end = content.find("</user_query>", q_content_start)
            next_asst = content.find("\nassistant:", q_content_start)
            if q_end != -1:
                user_content = content[q_content_start:q_end].strip()
            else:
                user_content = (content[q_content_start:next_asst].strip()
                                if next_asst != -1 else content[q_content_start:].strip())
            user_start_for_asst = q_open
        else:
            user_start = turn_start
            q_open = content.find("<user_query>", user_start)
            next_asst = content.find("\nassistant:", user_start)
            if q_open != -1 and (next_asst == -1 or q_open < next_asst):
                q_content_start = content.find("\n", q_open) + 1
                q_end = content.find("</user_query>", q_content_start)
                if q_end != -1:
                    user_content = content[q_content_start:q_end].strip()
                else:
                    user_content = (content[q_content_start:next_asst].strip()
                                    if next_asst != -1 else content[q_content_start:].strip())
            else:
                user_content_start = user_start + 6  # len("user:\n")
                user_content = (content[user_content_start:next_asst].strip()
                               if next_asst != -1 else content[user_content_start:].strip())
                if len(user_content) > 2000:
                    user_content = user_content[:2000] + "\n… [truncated]"
            user_start_for_asst = user_start

        if user_content:
            turns.append(("user", user_content))
        asst_start = content.find("\nassistant:", user_start_for_asst)
        if asst_start == -1:
            break
        asst_content_start = content.find("\n", asst_start + 1) + 1
        next_user_line = content.find("\nuser:\n", asst_content_start)
        next_query_tag = content.find("\n<user_query>", asst_content_start)
        next_user = next_user_line if next_user_line != -1 else len(content)
        if next_query_tag != -1 and next_query_tag < next_user:
            next_user = next_query_tag
        if next_user >= len(content):
            asst_raw = content[asst_content_start:].strip()
        else:
            asst_raw = content[asst_content_start:next_user].strip()
        think = re.search(r"<think>\s*.*?\s*</think>", asst_raw, re.DOTALL | re.IGNORECASE)
        if think:
            visible = asst_raw[think.end() :].strip()
        else:
            visible = asst_raw
        if visible:
            turns.append(("assistant", visible))
        pos = asst_content_start if next_user >= len(content) else next_user

    return turns


def in_work_window(mtime: datetime, report_date: datetime, start_hour: int, end_hour: int) -> bool:
    """
    True if mtime falls in [report_date at start_hour, day_end).
    If start_hour > end_hour (e.g. 3 AM to 1 AM): day_end is next day at end_hour.
    Otherwise (e.g. 9 to 17): day_end is same day at end_hour.
    """
    day_start = report_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if start_hour > end_hour:
        day_end = (report_date + timedelta(days=1)).replace(
            hour=end_hour, minute=0, second=0, microsecond=0
        )
    else:
        day_end = report_date.replace(
            hour=end_hour, minute=0, second=0, microsecond=0
        )
    return day_start <= mtime < day_end


def collect_transcripts(
    report_date: datetime,
    start_hour: int = 3,
    end_hour: int = 1,
) -> list[tuple[str, str, datetime, list[str], list[tuple[str, str]], str]]:
    """
    Returns list of (project_slug, project_path, last_modified, user_messages, full_turns, session_id).
    """
    workspace_paths = get_workspace_paths()
    results = []

    if not CURSOR_PROJECTS.exists():
        return results

    for project_dir in CURSOR_PROJECTS.iterdir():
        if not project_dir.is_dir():
            continue
        slug = project_dir.name
        if slug.startswith("tmp-"):
            continue
        transcripts_dir = project_dir / "agent-transcripts"
        if not transcripts_dir.exists():
            continue
        project_path = workspace_paths.get(slug) or slug_to_path(slug)

        for txt_file in transcripts_dir.glob("*.txt"):
            try:
                mtime = datetime.fromtimestamp(txt_file.stat().st_mtime)
                if not in_work_window(mtime, report_date, start_hour, end_hour):
                    continue
                content = txt_file.read_text(encoding="utf-8", errors="replace")
                full_turns = parse_transcript_full(content)
                user_messages = [c for r, c in full_turns if r == "user"]
                session_id = txt_file.stem
                results.append((slug, project_path, mtime, user_messages, full_turns, session_id))
            except Exception:
                continue

    return results


def _escape_fence(s: str, fence: str = "```") -> str:
    """Use a longer fence if content contains the default fence."""
    if fence in s:
        return "`" * 4
    return fence


# Placeholder when code/long content is removed so report stays light for AI
_CODE_OMITTED = "[کد/محتوای طولانی حذف شده]"


def _remove_fenced_blocks(text: str) -> str:
    """Replace ```...``` and ````...```` blocks with a short placeholder."""
    out = text
    # Match ``` or ````, optional lang, newline, content until closing fence
    for _ in range(100):  # limit iterations
        m = re.search(r"(`{3,})\w*\n.*?\n\1", out, re.DOTALL)
        if not m:
            break
        out = out[: m.start()] + _CODE_OMITTED + out[m.end() :]
    return out


def _shorten_tool_call_body(text: str) -> str:
    """
    Replace long 'contents:', 'old_string:', 'new_string:' values in [Tool call] blocks
    so the report stays short; keep path and tool name for context.
    """
    lines = text.split("\n")
    result: list[str] = []
    i = 0

    def is_key_line(ln: str) -> bool:
        s = ln.strip()
        return (s.startswith("path:") or s.startswith("contents:") or
                s.startswith("old_string:") or s.startswith("new_string:"))

    while i < len(lines):
        line = lines[i]
        # Skip long content after "contents:"
        if is_key_line(line) and "contents:" in line:
            result.append(line.split("contents:")[0].rstrip() + " contents: " + _CODE_OMITTED)
            i += 1
            while i < len(lines):
                if lines[i].startswith("[Tool") or is_key_line(lines[i]):
                    break
                i += 1
            continue
        # Skip long content after "old_string:"
        if is_key_line(line) and "old_string:" in line:
            result.append(line.split("old_string:")[0].rstrip() + " old_string: " + _CODE_OMITTED)
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith("new_string:") or lines[i].startswith("[Tool"):
                    break
                i += 1
            continue
        # Skip long content after "new_string:"
        if is_key_line(line) and "new_string:" in line:
            result.append(line.split("new_string:")[0].rstrip() + " new_string: " + _CODE_OMITTED)
            i += 1
            while i < len(lines):
                if lines[i].startswith("[Tool") or (is_key_line(lines[i]) and "old_string:" in lines[i]):
                    break
                i += 1
            continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _clean_assistant_content(raw: str) -> str:
    """
    Strip <think>, remove/shorten code blocks and long tool call bodies,
    so the report stays light for AI and focuses on what was done.
    """
    out = raw
    while True:
        m = re.search(r"<think>\s*.*?\s*</think>", out, re.DOTALL | re.IGNORECASE)
        if not m:
            break
        out = out[: m.start()].rstrip() + "\n\n" + out[m.end() :].lstrip()
    out = _remove_fenced_blocks(out)
    out = _shorten_tool_call_body(out)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def build_report(
    report_date: datetime,
    start_hour: int = 3,
    end_hour: int = 1,
    max_first_message_chars: int = 500,
    compact: bool = True,
) -> str:
    """
    Build markdown report for daily work.
    If compact=True (default): only project, time, and work summary (user requests).
    No full chat text — keeps report small for AI and human review.
    """
    rows = collect_transcripts(report_date, start_hour, end_hour)
    by_project: dict[tuple[str, str], list[tuple[datetime, list[str], list[tuple[str, str]], str]]] = {}
    for slug, path, mtime, messages, full_turns, session_id in rows:
        display = path_to_display_name(slug)
        key = (display, path)
        if key not in by_project:
            by_project[key] = []
        by_project[key].append((mtime, messages, full_turns, session_id))

    lines = []
    day_str = report_date.strftime("%Y-%m-%d")
    window_str = f"{start_hour}:00 – next day {end_hour}:00"
    lines.append(f"# Cursor Daily Work Report — {day_str}")
    lines.append("")
    lines.append(f"Time window: **{window_str}** (based on file last-modified time).")
    lines.append("")
    lines.append("---")
    lines.append("")

    for (display_name, path) in sorted(by_project.keys(), key=lambda x: x[0].lower()):
        items = by_project[(display_name, path)]
        items.sort(key=lambda x: x[0])
        lines.append(f"## {display_name}")
        lines.append("")
        lines.append(f"**Path:** `{path}`")
        lines.append("")

        for i, (mtime, all_msgs, full_turns, session_id) in enumerate(items, 1):
            lines.append(f"### Chat {i} — {mtime.strftime('%Y-%m-%d %H:%M')}")
            lines.append("")
            lines.append(f"**کارهای درخواست‌شده ({len(all_msgs)} مورد):**")
            lines.append("")
            for j, msg in enumerate(all_msgs, 1):
                preview = msg.strip()
                if len(preview) > max_first_message_chars:
                    preview = preview[:max_first_message_chars] + "…"
                lines.append(f"{j}. {preview}")
                if "\n" in preview:
                    lines.append("")
            if not compact:
                lines.append("")
                lines.append("**Specs:**")
                lines.append(f"- Session ID: `{session_id}`")
                lines.append(f"- Last activity: {mtime.strftime('%Y-%m-%d %H:%M')}")
                lines.append(f"- Total turns: {len(full_turns)}")
                lines.append("")
                lines.append("**Full chat:**")
                lines.append("")
                for role, content in full_turns:
                    label = "**User**" if role == "user" else "**Assistant**"
                    lines.append(label)
                    lines.append("")
                    clean = _clean_assistant_content(content) if role == "assistant" else content
                    fence = _escape_fence(clean)
                    lines.append(fence)
                    lines.append(clean.strip())
                    lines.append(fence)
                    lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("")

    if not by_project:
        lines.append("*No Cursor agent transcripts found in the selected time window.*")
        lines.append("")
        lines.append("Make sure you use Cursor in Agent/Composer mode so that transcripts are saved under `~/.cursor/projects/<project>/agent-transcripts/`.")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a daily work report from Cursor agent transcripts."
    )
    ap.add_argument(
        "--date",
        type=str,
        default=None,
        help="Report date YYYY-MM-DD (default: today).",
    )
    ap.add_argument(
        "--start",
        type=int,
        default=3,
        help="Start hour of work day (0–23). Default 3 = 3 AM.",
    )
    ap.add_argument(
        "--end",
        type=int,
        default=1,
        help="End hour of work day (0–23), next day. Default 1 = 1 AM next day.",
    )
    ap.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write report to this file (default: print to stdout).",
    )
    ap.add_argument(
        "--max-chars",
        type=int,
        default=500,
        help="Max characters for first user message in report (default 500).",
    )
    ap.add_argument(
        "--full",
        action="store_true",
        help="Include full chat text (default: compact, only work summary).",
    )
    args = ap.parse_args()

    if args.date:
        try:
            report_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("Invalid --date; use YYYY-MM-DD.")
            return
    else:
        report_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    report = build_report(
        report_date,
        start_hour=args.start,
        end_hour=args.end,
        max_first_message_chars=args.max_chars,
        compact=not args.full,
    )

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
