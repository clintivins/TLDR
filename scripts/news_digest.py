from __future__ import annotations

import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate
from html import unescape
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


def build_digest() -> tuple[str, str]:
    now = datetime.now(TIMEZONE)
    sections = []
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
        sections.append("\n".join(lines))

    subject = f"BDO Digital news digest - {now:%d %B %Y} ({total} stories)"
    body = (
        f"BDO Digital news digest\n{now:%A, %d %B %Y at %H:%M %Z}\n\n"
        + "\n\n".join(sections)
        + "\n\nSources are public Google News RSS results."
    )
    return subject, body


def send_email(subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = required("SMTP_FROM")
    message["To"] = required("NEWS_EMAIL_TO")
    message["Date"] = formatdate(localtime=True)
    message["Subject"] = subject
    message.set_content(body)

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
    subject, body = build_digest()
    send_email(subject, body)
    print(subject)