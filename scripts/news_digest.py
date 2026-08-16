from __future__ import annotations

import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate
from html import escape, unescape
from time import mktime
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET


TIMEZONE = ZoneInfo("Europe/London")
FEEDS = {
    "United Kingdom": "BDO Digital UK",
    "United States": "BDO Digital USA",
    "Canada": "BDO Digital Canada",
}
USER_AGENT = "BDO-Digital-News-Digest/1.0 (+https://github.com/clintivins/TLDR)"


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def clean(value: str) -> str:
    return " ".join(unescape(value).split())


def google_news_feed(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=en-GB&gl=GB&ceid=GB:en"
    )


def fetch_items(region: str, query: str) -> list[dict[str, str]]:
    request = Request(google_news_feed(query), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())

    items = []
    for item in root.findall("./channel/item")[:10]:
        title = clean(item.findtext("title", ""))
        link = item.findtext("link", "")
        source = clean(item.findtext("source", "Google News"))
        published = clean(item.findtext("pubDate", ""))
        if title and link:
            items.append(
                {
                    "region": region,
                    "title": title,
                    "link": link,
                    "source": source,
                    "published": published,
                }
            )
    return items


def build_digest() -> tuple[str, str, str]:
    now = datetime.now(TIMEZONE)
    text_sections = []
    html_sections = []
    total = 0
    for region, query in FEEDS.items():
        try:
            items = fetch_items(region, query)
        except Exception as error:
            print(f"Could not fetch {region}: {error}", file=sys.stderr)
            items = []
        total += len(items)
        lines = [f"{region}", "=" * len(region)]
        if items:
            lines.extend(
                f"- {item['title']} ({item['source']}, {item['published']})\n  {item['link']}"
                for item in items
            )
        else:
            lines.append("No matching stories were available today.")
        text_sections.append("\n".join(lines))

        if items:
            stories = "".join(
                "<li style='margin:0 0 18px;padding:0 0 18px;border-bottom:1px solid #e5e7eb;'>"
                f"<a href='{escape(item['link'], quote=True)}' style='color:#155e75;font-size:16px;font-weight:700;text-decoration:none;'>"
                f"{escape(item['title'])}</a>"
                f"<div style='color:#64748b;font-size:12px;margin-top:6px;'>"
                f"{escape(item['source'])} &middot; {escape(item['published'])}</div></li>"
                for item in items
            )
        else:
            stories = "<li style='color:#64748b;'>No matching stories were available today.</li>"
        html_sections.append(
            f"<section style='margin:0 0 28px;'><h2 style='color:#0f3d4c;font-size:20px;"
            f"margin:0 0 12px;padding-bottom:8px;border-bottom:3px solid #f59e0b;'>"
            f"{escape(region)}</h2><ul style='list-style:none;margin:0;padding:0;'>{stories}</ul></section>"
        )

    subject = f"BDO Digital news digest - {now:%d %B %Y} ({total} stories)"
    body = (
        f"BDO Digital news digest\n{now:%A, %d %B %Y at %H:%M %Z}\n\n"
        + "\n\n".join(text_sections)
        + "\n\nSources are public Google News RSS results."
    )
    html_body = (
        "<!doctype html><html><body style='margin:0;background:#f1f5f9;"
        "font-family:Arial,sans-serif;color:#1e293b;'>"
        "<div style='max-width:680px;margin:0 auto;padding:28px 18px;'>"
        "<header style='background:#0f3d4c;color:white;padding:28px 30px;border-radius:8px 8px 0 0;'>"
        "<div style='font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#fbbf24;'>Daily briefing</div>"
        "<h1 style='font-size:30px;line-height:1.15;margin:8px 0 10px;'>BDO Digital news digest</h1>"
        f"<div style='font-size:14px;color:#dbeafe;'>{escape(now.strftime('%A, %d %B %Y at %H:%M %Z'))}</div>"
        "</header><main style='background:white;padding:28px 30px;'>"
        + "".join(html_sections)
        + "</main><footer style='padding:16px 30px;color:#64748b;font-size:12px;"
        "background:#e2e8f0;border-radius:0 0 8px 8px;'>"
        "Sources are public Google News RSS results.</footer></div></body></html>"
    )
    return subject, body, html_body


def send_email(subject: str, body: str, html_body: str) -> None:
    message = EmailMessage()
    message["From"] = required("SMTP_FROM")
    message["To"] = required("NEWS_EMAIL_TO")
    message["Date"] = formatdate(localtime=True)
    message["Subject"] = subject
    message.set_content(body)
    message.add_alternative(html_body, subtype="html")

    host = required("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "465"))
    username = required("SMTP_USERNAME")
    password = required("SMTP_PASSWORD")
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.send_message(message)


if __name__ == "__main__":
    # The two UTC schedules above overlap at one local hour each day. Only
    # the invocation that lands at 07:00 in London should send. Manual runs
    # are always allowed so the workflow can be tested immediately.
    is_scheduled_run = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    if is_scheduled_run and datetime.now(timezone.utc).astimezone(TIMEZONE).hour != 7:
        print("Not 07:00 Europe/London; skipping this scheduled invocation.")
        raise SystemExit(0)
    subject, body, html_body = build_digest()
    send_email(subject, body, html_body)
    print(subject)