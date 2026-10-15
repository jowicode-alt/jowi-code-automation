"""Conservative RSS-based international news monitor.

Only queues a news candidate when two different configured publishers report
similar headlines. It records source URLs for the private draft description.
This is a discovery/corroboration gate, not a guarantee that every claim is true;
a human/source review remains required before public release.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET

import httpx

from app.jobs import _database, _query, enqueue_job

FEEDS = (
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Guardian World", "https://www.theguardian.com/world/rss"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
    ("UN News", "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
)
USER_AGENT = "TheJowiCodeNewsMonitor/1.0 (+original summaries; contact channel owner)"
MAX_FEED_BYTES = 2_000_000
RECENT_HOURS = 36
MIN_SHARED_TOKEN_RATIO = 0.34
STOPWORDS = {
    "about", "after", "against", "amid", "among", "and", "are", "around",
    "before", "between", "breaking", "from", "have", "into", "latest", "more",
    "over", "says", "that", "the", "their", "there", "these", "this", "today",
    "update", "was", "were", "what", "when", "where", "which", "while", "with",
}


def _tokens(title: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", title.lower())
        if token not in STOPWORDS
    }


def _similarity(first: str, second: str) -> float:
    a, b = _tokens(first), _tokens(second)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _parse_date(value: str) -> datetime:
    try:
        result = parsedate_to_datetime(value)
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return datetime.now(timezone.utc)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed(xml_text: str, source_name: str, feed_url: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for element in root.iter():
        if _local_name(element.tag) not in {"item", "entry"}:
            continue
        fields = {}
        for child in element:
            name = _local_name(child.tag)
            if name == "link":
                link = child.attrib.get("href") or (child.text or "").strip()
                if child.attrib.get("rel", "alternate") == "alternate":
                    fields["link"] = link
            elif name in {"title", "pubdate", "published", "updated", "date", "description", "summary", "encoded"}:
                # RSS descriptions often contain the only accessible publisher-written
                # article summary. Keep it bounded and strip markup before storage.
                raw = "".join(child.itertext()).strip()
                if name in {"description", "summary", "encoded"}:
                    raw = re.sub(r"<[^>]+>", " ", html.unescape(raw))
                    raw = " ".join(raw.split())
                    fields[name] = raw[:3000]
                else:
                    fields[name] = raw
        title = fields.get("title", "").strip()
        link = fields.get("link", "").strip()
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        published = fields.get("pubdate") or fields.get("published") or fields.get("updated") or fields.get("date") or ""
        summary = fields.get("description") or fields.get("summary") or fields.get("encoded") or ""
        # Do not let a bare duplicate headline masquerade as article-level evidence.
        if summary.strip().lower() == title.strip().lower():
            summary = ""
        items.append({
            "title": title[:240],
            "url": link[:2000],
            "source": source_name,
            "feed_url": feed_url,
            "summary": summary[:3000],
            "published_at": _parse_date(published).isoformat(),
        })
    return items


def _ensure_tables(db, is_postgres: bool) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS news_events (
        event_key TEXT PRIMARY KEY,
        topic TEXT NOT NULL,
        sources_json TEXT NOT NULL,
        first_seen_utc TEXT NOT NULL,
        updated_at_utc TEXT NOT NULL
    )""")


def _event_key(topic: str) -> str:
    return hashlib.sha256(" ".join(topic.lower().split()).encode("utf-8")).hexdigest()


def _store_event(topic: str, sources: list[dict]) -> None:
    key = _event_key(topic)
    now = datetime.now(timezone.utc).isoformat()
    with _database() as (db, is_postgres):
        _ensure_tables(db, is_postgres)
        existing = db.execute(
            _query("SELECT first_seen_utc FROM news_events WHERE event_key = ?", is_postgres),
            (key,),
        ).fetchone()
        first_seen = existing[0] if existing else now
        db.execute(
            _query(
                "INSERT INTO news_events (event_key, topic, sources_json, first_seen_utc, updated_at_utc) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(event_key) DO UPDATE SET "
                "sources_json = excluded.sources_json, updated_at_utc = excluded.updated_at_utc",
                is_postgres,
            ),
            (key, topic, json.dumps(sources), first_seen, now),
        )


def sources_for_topic(topic: str) -> list[dict]:
    with _database() as (db, is_postgres):
        _ensure_tables(db, is_postgres)
        row = db.execute(
            _query("SELECT sources_json FROM news_events WHERE event_key = ?", is_postgres),
            (_event_key(topic),),
        ).fetchone()
    if not row:
        return []
    try:
        return json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return []


def scan_once(client: httpx.Client | None = None) -> dict:
    """Fetch bounded RSS feeds, require cross-publisher headline overlap, queue once."""
    own_client = client is None
    http = client or httpx.Client(
        timeout=httpx.Timeout(8.0, connect=4.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    articles: list[dict] = []
    feed_errors = []
    try:
        for source, url in FEEDS:
            try:
                response = http.get(url)
                response.raise_for_status()
                if len(response.content) > MAX_FEED_BYTES:
                    feed_errors.append({"source": source, "error": "feed exceeded size limit"})
                    continue
                articles.extend(parse_feed(response.text, source, url))
            except Exception as exc:
                feed_errors.append({"source": source, "error": type(exc).__name__})
    finally:
        if own_client:
            http.close()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_HOURS)
    recent = [
        item for item in articles
        if _parse_date(item["published_at"]) >= cutoff and len(_tokens(item["title"])) >= 3
    ]
    recent.sort(key=lambda item: item["published_at"], reverse=True)
    queued = []
    seen_keys = set()
    for article in recent:
        matching = [
            other for other in recent
            if other["source"] != article["source"]
            and _similarity(article["title"], other["title"]) >= MIN_SHARED_TOKEN_RATIO
        ]
        sources_by_name = {article["source"]: article}
        for other in matching:
            sources_by_name.setdefault(other["source"], other)
        if len(sources_by_name) < 2:
            continue
        cluster_keys = {_event_key(article["title"])}
        cluster_keys.update(_event_key(other["title"]) for other in matching)
        if cluster_keys & seen_keys:
            continue
        seen_keys.update(cluster_keys)
        sources = list(sources_by_name.values())[:4]
        _store_event(article["title"], sources)
        job = enqueue_job("breaking_news", article["title"])
        queued.append({
            "topic": article["title"],
            "job_id": job["id"],
            "deduplicated": bool(job.get("deduplicated", False)),
            "source_count": len(sources),
        })
    with _database() as (db, is_postgres):
        pending_news_jobs = db.execute(
            _query(
                "SELECT COUNT(*) FROM jobs WHERE job_type = ? AND status = ?",
                is_postgres,
            ),
            ("breaking_news", "queued"),
        ).fetchone()[0]
    return {
        "feeds_checked": len(FEEDS),
        "pending_news_jobs": int(pending_news_jobs),
        "articles_seen": len(articles),
        "recent_articles": len(recent),
        "candidates": len(queued),
        "queued": queued,
        "feed_errors": feed_errors,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    print(json.dumps(scan_once(), ensure_ascii=False))
