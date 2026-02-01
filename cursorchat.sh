#!/usr/bin/env bash

# تاریخ امروز
TODAY=$(date +%Y-%m-%d)
OUTPUT="$HOME/cursor/cursor-chats-$TODAY.md"

echo "# چت‌های Cursor - $TODAY" > "$OUTPUT"
echo "" >> "$OUTPUT"

# پیدا کردن دیتابیس‌های اخیر (تغییر در ۲-۳ روز گذشته)
find ~/.config/Cursor/User/workspaceStorage \
     -type f -name state.vscdb -mtime -3 2>/dev/null | sort | while read -r db; do

    echo "" >> "$OUTPUT"
    echo "## از دیتابیس: $(basename "$(dirname "$db")")" >> "$OUTPUT"
    echo "" >> "$OUTPUT"

    # استخراج کلیدهای چت + محتوای آن‌ها
    sqlite3 "$db" \
        "SELECT key, value FROM ItemTable WHERE key LIKE 'chat-%'" 2>/dev/null | while IFS=$'\t' read -r key value; do

        # فقط چت‌هایی که امروز در آن‌ها چیزی نوشته شده (تقریباً)
        if echo "$value" | grep -qi "$(date +%Y-%m-%d)"; then

            # عنوان چت (اگر موجود باشد)
            title=$(echo "$value" | grep -oP '(?<="title":")[^"]*' | head -1 || echo "بدون عنوان")

            echo "### $title" >> "$OUTPUT"
            echo "" >> "$OUTPUT"

            # تلاش برای نمایش پیام‌ها به شکل خوانا
            echo "$value" | grep -oP '"role":"[^"]+","content":"[^"]+"' | while read -r line; do
                role=$(echo "$line" | grep -oP '(?<="role":")[^"]+')
                content=$(echo "$line" | grep -oP '(?<="content":")[^"]+' | sed 's/\\n/\n/g')

                if [[ "$role" == "user" ]]; then
                    echo "**شما:**" >> "$OUTPUT"
                else
                    echo "**Cursor:**" >> "$OUTPUT"
                fi
                echo "$content" >> "$OUTPUT"
                echo "" >> "$OUTPUT"
            done

            echo "---" >> "$OUTPUT"
            echo "" >> "$OUTPUT"
        fi
    done
done

echo "فایل ایجاد شد →  $OUTPUT"
echo "اگر خالی بود، یعنی چت امروز پیدا نشد یا ساختار دیتابیس تغییر کرده."
wc -l "$OUTPUT"#!/usr/bin/env bash

set -euo pipefail

TODAY=$(date +%Y-%m-%d)
OUTPUT_MD="$$   HOME/Desktop/cursor-chats-   $${TODAY}.md"

echo "# چت‌های Cursor امروز - ${TODAY}" > "$OUTPUT_MD"
echo "" >> "$OUTPUT_MD"

# پیدا کردن همه state.vscdb هایی که امروز تغییر کردن
find ~/.config/Cursor/User/workspaceStorage \
  -type f -name 'state.vscdb' -mtime -1 2>/dev/null | while read -r db; do

  workspace=$$   (basename "   $$(dirname "$db")")

  echo "" >> "$OUTPUT_MD"
  echo "## Workspace: ${workspace:0:12}..." >> "$OUTPUT_MD"
  echo "" >> "$OUTPUT_MD"

  # استخراج چت‌ها (تقریباً همه پیام‌ها با زمان)
  sqlite3 -noheader -separator $'\t' "$db" \
    "SELECT substr(key,1,40) as chat_id, value
     FROM ItemTable
     WHERE key LIKE 'chat-%'
       AND value LIKE '%\"messages\":%' " 2>/dev/null | while read -r chat_id value; do

    # چک کردن اینکه آیا امروز هست یا نه
    if echo "$$   value" | grep -q "\"createdAt\":\"   $${TODAY}"; then

      # تلاش برای گرفتن عنوان (اختیاری)
      title=$(echo "$value" | grep -oP '(?<="title":")[^"]+' || echo "بدون عنوان")

      echo "### $$   {title:-بدون عنوان}  (   $${chat_id:0:8}...)" >> "$OUTPUT_MD"
      echo "" >> "$OUTPUT_MD"

      # استخراج پیام‌ها به صورت خواناتر
      echo "$value" | jq -r '.messages[] | 
        if .role == "user" then "**You:** " + .content 
        elif .role == "assistant" then "**Cursor:** " + .content 
        else "- " + .role + ": " + .content end' 2>/dev/null >> "$OUTPUT_MD" || {

        # اگر jq نبود یا خطا داد، خام می‌ریزیم
        echo "(خطا در پارس پیام‌ها - محتوای خام:)" >> "$OUTPUT_MD"
        echo "$value" | head -n 20 >> "$OUTPUT_MD"
      }

      echo "" >> "$OUTPUT_MD"
      echo "---" >> "$OUTPUT_MD"
      echo "" >> "$OUTPUT_MD"

    fi
  done
done

echo "" >> "$OUTPUT_MD"
echo "فایل ساخته شد:  $OUTPUT_MD"
echo "تعداد خطوط: $(wc -l < "$OUTPUT_MD")"

