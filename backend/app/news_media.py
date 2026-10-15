"""Source-grounded breaking-news package with freely licensed moving footage.

This deliberately fails closed: a news Short is not uploaded unless it has readable
reporting from at least two independent sources and relevant, openly licensed video.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import time
from urllib.parse import quote

import httpx

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "TheJowiCodeNewsBot/1.0 (news video; contact channel owner)"
VIDEO_EXTENSIONS = (".webm", ".ogv", ".ogg", ".mp4", ".mov")
ALLOWED_LICENSES = ("CC0", "Public domain", "CC BY", "CC BY-SA", "Creative Commons Attribution")
MAX_VIDEO_BYTES = 35 * 1024 * 1024


class _ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_paragraph = False
        self.in_title = False
        self.paragraphs: list[str] = []
        self.title_parts: list[str] = []
        self.current: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "p":
            self.in_paragraph = True
            self.current = []
        if tag == "title":
            self.in_title = True
        if tag in {"script", "style", "nav", "footer", "header"}:
            self.in_paragraph = False

    def handle_endtag(self, tag):
        if tag == "p" and self.in_paragraph:
            value = " ".join(" ".join(self.current).split())
            if len(value) >= 70:
                self.paragraphs.append(value)
            self.in_paragraph = False
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        value = data.strip()
        if not value:
            return
        if self.in_paragraph:
            self.current.append(value)
        if self.in_title:
            self.title_parts.append(value)


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.strip()) >= 35]


def _fetch_reporting(sources: list[dict], client: httpx.Client) -> tuple[list[str], list[dict]]:
    evidence: list[str] = []
    usable_sources: list[dict] = []
    for source in sources[:4]:
        url = str(source.get("url", ""))
        if not url.startswith("https://"):
            continue
        try:
            response = client.get(url, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            parser = _ArticleText()
            parser.feed(response.text[:2_000_000])
            paragraphs = parser.paragraphs
            # Prefer short, factual lead paragraphs. Avoid reusing the headline as the script.
            selected = []
            for paragraph in paragraphs[:10]:
                for sentence in _sentences(paragraph):
                    if len(sentence) > 360:
                        continue
                    if sentence not in selected:
                        selected.append(sentence)
                    if len(selected) >= 3:
                        break
                if len(selected) >= 3:
                    break
            if selected:
                evidence.extend(selected)
                usable_sources.append({
                    "source": str(source.get("source", "News source")),
                    "url": url,
                    "facts": selected,
                })
        except Exception as exc:
            print(f"News article fetch failed for {source.get('source', 'source')}: {type(exc).__name__}", flush=True)
    return evidence, usable_sources


def _script(topic: str, sources: list[dict], facts: list[str]) -> str:
    # Select details across publishers rather than taking every sentence from one page.
    unique = []
    seen = set()
    max_sentences = max((len(item.get("facts", [])) for item in sources), default=0)
    for index in range(max_sentences):
        for source in sources:
            source_facts = source.get("facts", [])
            if index >= len(source_facts):
                continue
            sentence = source_facts[index]
            key = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(sentence)
    if len(unique) < 3 or len(sources) < 2:
        raise RuntimeError("Not enough article-level evidence from two independent sources for a factual news script")
    chosen = unique[:6]
    outlet_names = list(dict.fromkeys(item["source"] for item in sources))
    intro = f"Here is the developing story: {topic}. "
    context = "Reporting from " + ", ".join(outlet_names[:3]) + " provides the following details. "
    body = " ".join(chosen)
    caution = (
        "These are the details available in the linked reporting at the time this draft was prepared. "
        "Information may change as the story develops, so check the original reports for updates. "
        "Subscribe to The Jowi Code for clear, sourced news. Thanks for watching."
    )
    return intro + context + body + " " + caution


def _video_results(topic: str, client: httpx.Client) -> list[dict]:
    # Query Commons for actual video files only; no generic generated illustrations.
    query = re.sub(r"[^\w\s-]", " ", topic)
    query = " ".join(query.split()[:8])
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{query} filemime:video", "gsrnamespace": 6,
        "gsrlimit": 30, "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size",
    }
    response = client.get(COMMONS_API, params=params, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url", "")
        if not url.lower().endswith(VIDEO_EXTENSIONS):
            continue
        metadata = info.get("extmetadata") or {}
        license_name = re.sub("<[^>]+>", "", metadata.get("LicenseShortName", {}).get("value", ""))
        license_lower = license_name.lower()
        if "nc" in license_lower or "noncommercial" in license_lower or "nd" in license_lower or "noderivatives" in license_lower:
            continue
        if not any(allowed.lower() in license_lower for allowed in ALLOWED_LICENSES):
            continue
        topic_terms = {word for word in re.findall(r"[a-z0-9]{4,}", query.lower())}
        title_terms = {word for word in re.findall(r"[a-z0-9]{4,}", page.get("title", "").lower())}
        overlap = len(topic_terms & title_terms)
        if topic_terms and overlap < (2 if len(topic_terms) >= 3 else 1):
            continue
        if int(info.get("size", 0) or 0) > MAX_VIDEO_BYTES:
            continue
        results.append({
            "title": page.get("title", "Wikimedia Commons video"),
            "url": url,
            "license": license_name,
            "artist": re.sub("<[^>]+>", "", metadata.get("Artist", {}).get("value", "Unknown")),
            "page": "https://commons.wikimedia.org/wiki/" + quote(page.get("title", "").replace(" ", "_")),
            "size": int(info.get("size", 0) or 0),
        })
    return results


def build_news_package(topic: str, sources: list[dict], output_dir: str) -> dict:
    """Download licensed moving footage and construct narration from fetched article facts."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timeout = httpx.Timeout(12.0, connect=6.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        facts, usable_sources = _fetch_reporting(sources, client)
        if len(usable_sources) < 2:
            raise RuntimeError("News blocked: could not retrieve article-level reporting from two independent publishers")
        narration = _script(topic, usable_sources, facts)
        candidates = _video_results(topic, client)
        if not candidates:
            raise RuntimeError("News blocked: no topic-matched Wikimedia Commons video with an accepted free license was found")
        clips = []
        attributions = []
        for candidate in candidates:
            if len(clips) >= 4:
                break
            try:
                response = client.get(candidate["url"], headers={"User-Agent": USER_AGENT})
                response.raise_for_status()
                data = response.content
                if not data or len(data) > MAX_VIDEO_BYTES:
                    continue
                suffix = Path(candidate["url"].split("?", 1)[0]).suffix.lower()
                if suffix not in VIDEO_EXTENSIONS:
                    continue
                path = directory / f"news-clip-{len(clips) + 1}{suffix}"
                path.write_bytes(data)
                if path.stat().st_size < 1024:
                    path.unlink(missing_ok=True)
                    continue
                clips.append(str(path))
                attributions.append({
                    "title": candidate["title"],
                    "creator": candidate["artist"],
                    "license": candidate["license"],
                    "source_url": candidate["page"],
                })
            except Exception as exc:
                print(f"Licensed clip download failed: {type(exc).__name__}", flush=True)
        if not clips:
            raise RuntimeError("News blocked: no usable licensed moving footage could be downloaded")
        return {
            "narration": narration,
            "clips": clips,
            "clip_attributions": attributions,
            "sources": usable_sources,
            "footage_provider": "Wikimedia Commons",
        }
