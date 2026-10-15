"""Source-grounded breaking-news package with freely licensed moving footage.

This deliberately fails closed: a news Short is not uploaded unless it has readable
reporting from at least two independent sources and relevant, openly licensed video.
"""
from __future__ import annotations

from html.parser import HTMLParser
from html import unescape
from pathlib import Path
import re
import time
from urllib.parse import quote

import httpx

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "TheJowiCodeNewsBot/1.0 (https://github.com/jowicode-alt/jowi-code-automation) httpx"
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
            response = None
            # Retry transient publisher timeouts/rate limits, without spending the whole
            # job budget on one publisher. RSS summaries below are the fallback evidence.
            for attempt in range(3):
                try:
                    response = client.get(url, headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(18.0, connect=8.0))
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                    if attempt == 2:
                        raise exc
                    time.sleep(1.0 + attempt * 1.5)
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
            # RSS descriptions are publisher-authored reporting snippets. They are
            # a useful fallback when the full article blocks bots or times out.
            if len(selected) < 2:
                summary = unescape(re.sub(r"<[^>]+>", " ", str(source.get("summary", ""))))
                summary = " ".join(summary.split())
                if len(summary) >= 100:
                    for sentence in _sentences(summary):
                        if len(sentence) <= 360 and sentence not in selected:
                            selected.append(sentence)
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


def _fallback_script(topic: str, sources: list[dict]) -> str:
    """Build a conservative, source-attributed script when hosted generation is unavailable.

    This avoids inventing details and avoids long verbatim excerpts: use at most one
    short excerpt from each of two publishers, clearly attributed, with neutral framing.
    """
    excerpts = []
    for source in sources:
        facts = source.get("facts") or []
        if not facts:
            continue
        # Keep each publisher's excerpt short; the rest is original neutral narration.
        excerpt = " ".join(str(facts[0]).split())
        words = excerpt.split()
        if len(words) > 20:
            excerpt = " ".join(words[:20]).rstrip(" ,;:") + "…"
        excerpts.append((str(source.get("source", "a news publisher")), excerpt))
        if len(excerpts) == 2:
            break
    if len(excerpts) < 2:
        raise RuntimeError("Fallback news narration requires two independent reporting sources")
    return (
        f"Here is a developing news update about {topic}. "
        f"{excerpts[0][0]} reports: “{excerpts[0][1]}” "
        f"A separate report from {excerpts[1][0]} provides another account: “{excerpts[1][1]}” "
        "These are short excerpts from the linked reporting, not a complete account of the event. "
        "The available reports should be read in context, and details may change as journalists "
        "publish corrections or additional confirmed information. We are not adding unverified claims "
        "or guessing about causes, responsibility, or what may happen next. Check both original reports "
        "in the video description for the full context and any later updates. "
        "Subscribe to The Jowi Code for clear, sourced news. Thanks for watching."
    )


def _script(topic: str, sources: list[dict], facts: list[str], client: httpx.Client) -> str:
    """Ask the free AI Horde text-generation pool for an original, evidence-bounded script."""
    if len(facts) < 3 or len(sources) < 2:
        raise RuntimeError("Not enough article-level evidence from two independent sources for a factual news script")
    base_url = __import__("os").getenv("AI_HORDE_BASE_URL", "https://aihorde.net/api").rstrip("/")
    api_key = __import__("os").getenv("AI_HORDE_API_KEY", "0000000000").strip() or "0000000000"
    evidence = []
    for source in sources:
        evidence.append(f"Publisher: {source['source']}\nURL: {source['url']}\nReported details:\n- " + "\n- ".join(source["facts"]))
    prompt = (
        "Write an original spoken YouTube Shorts breaking-news script in clear international English. "
        "Target 100 to 150 words. Use only facts explicitly supported by the source notes below. "
        "Do not invent numbers, dates, names, causes, motives, quotes, or outcomes. Do not copy sentences "
        "from the notes; paraphrase in original wording. Attribute disputed or uncertain details. If sources "
        "disagree, explain that they differ rather than choosing one. Structure: what happened, the strongest "
        "confirmed details, why it matters, what remains unknown, and a brief reminder that details may change. "
        "End exactly with: Subscribe to The Jowi Code for clear, sourced news. Thanks for watching. "
        "Return only the narration, with no heading, bullets, citations list, or production notes.\n\n"
        f"Topic: {topic}\n\nSOURCE NOTES (evidence only, not text to copy):\n"
        + "\n\n".join(evidence)
        + "\n\nOriginal spoken script:"
    )
    headers = {
        "apikey": api_key,
        "Client-Agent": "TheJowiCodeAutomation:0.1.0:github.com/jowicode-alt/jowi-code-automation",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "params": {
            "max_length": 280,
            "max_context_length": 4096,
            "temperature": 0.35,
            "top_p": 0.9,
            "rep_pen": 1.08,
        },
        "nsfw": False,
        "trusted_workers": False,
        "slow_workers": False,
        "dry_run": False,
    }
    response = client.post(f"{base_url}/v2/generate/text/async", headers=headers, json=payload)
    # A stale or restricted configured key can be rejected before a request is queued.
    # Retry exactly once with AI Horde's documented anonymous key; this remains free,
    # though it may have lower priority or be restricted during provider high load.
    if response.status_code in {401, 403} and api_key != "0000000000":
        print(
            f"AI Horde rejected configured credentials (HTTP {response.status_code}); "
            "retrying once with the documented anonymous key.",
            flush=True,
        )
        headers = {**headers, "apikey": "0000000000"}
        response = client.post(f"{base_url}/v2/generate/text/async", headers=headers, json=payload)
    if response.status_code in {401, 403}:
        print(
            f"AI Horde denied text generation (HTTP {response.status_code}); "
            "using conservative source-attributed narration fallback.",
            flush=True,
        )
        return _fallback_script(topic, sources)
    response.raise_for_status()
    request_id = response.json().get("id")
    if not request_id:
        raise RuntimeError("AI Horde did not return a text-generation request ID")
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status_response = client.get(
            f"{base_url}/v2/generate/text/status/{request_id}", headers=headers
        )
        status_response.raise_for_status()
        status = status_response.json()
        if status.get("faulted"):
            raise RuntimeError("AI Horde text generation failed")
        generations = status.get("generations") or []
        if generations:
            narration = " ".join(str(generations[0].get("text", "")).split()).strip().strip('"')
            word_count = len(narration.split())
            if word_count < 75 or word_count > 190:
                raise RuntimeError(f"AI-generated news script has invalid length ({word_count} words)")
            if "The Jowi Code" not in narration or "Thanks for watching" not in narration:
                raise RuntimeError("AI-generated news script is missing the required channel sign-off")
            return narration
        time.sleep(3)
    raise TimeoutError("AI Horde text generation did not finish within 180 seconds")


def _video_results(topic: str, client: httpx.Client) -> list[dict]:
    """Search several focused Commons queries, then rank only relevant, licensed videos.

    The topic may be a long headline rather than the words used in a Commons file title.
    Try the original phrase, compact keyword combinations, and individual meaningful terms.
    Relevance is checked against both the file title and its description; licence checks
    remain mandatory and a missing/unclear licence is never treated as permission.
    """
    stop_words = {
        "about", "after", "amid", "among", "around", "before", "being", "between",
        "breaking", "could", "during", "from", "have", "into", "latest", "near",
        "over", "says", "that", "their", "there", "these", "this", "today", "update",
        "what", "when", "where", "which", "while", "with", "would", "your", "news",
        "video", "footage", "report", "reports",
    }
    topic_terms = []
    for word in re.findall(r"[a-z0-9]{3,}", topic.lower()):
        if word not in stop_words and word not in topic_terms:
            topic_terms.append(word)
    if not topic_terms:
        return []

    # Use bounded, serial requests to be kind to Commons' shared API.
    queries = []
    clean_topic = " ".join(re.findall(r"[\w-]+", topic))[:120].strip()
    if clean_topic:
        queries.append(clean_topic)
    if len(topic_terms) >= 2:
        queries.append(" ".join(topic_terms[:4]))
        queries.append(" ".join(topic_terms[:2]))
    queries.extend(topic_terms[:4])
    unique_queries = []
    for query in queries:
        if query and query.casefold() not in {q.casefold() for q in unique_queries}:
            unique_queries.append(query)

    candidates_by_title = {}
    for query in unique_queries[:5]:
        params = {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"{query} filemime:video", "gsrnamespace": 6,
            "gsrlimit": 30, "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
        }
        response = client.get(COMMONS_API, params=params, headers={"User-Agent": USER_AGENT})
        if response.status_code == 403:
            raise RuntimeError(
                "Wikimedia Commons denied the API request (HTTP 403). The client sends a "
                "descriptive User-Agent with a contact URL; do not bypass the denial or use "
                "unverified footage. Check the response details and retry later if access is "
                "temporarily restricted."
            )
        if response.status_code in {429, 503}:
            # Respect provider throttling/temporary overload; do not fan out more requests.
            print(f"Wikimedia Commons search temporarily unavailable (HTTP {response.status_code}).", flush=True)
            break
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title", "")
            if not title:
                continue
            candidates_by_title.setdefault(title, (page, query))
        if len(candidates_by_title) >= 100:
            break

    results = []
    for page, matched_query in candidates_by_title.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url", "")
        mime = str(info.get("mime", "")).lower()
        if not url.lower().split("?", 1)[0].endswith(VIDEO_EXTENSIONS) and not mime.startswith("video/"):
            continue
        metadata = info.get("extmetadata") or {}
        license_name = re.sub(r"<[^>]+>", " ", str(metadata.get("LicenseShortName", {}).get("value", "")))
        license_name = " ".join(unescape(license_name).split())
        license_lower = license_name.lower()
        restricted_license = (
            "noncommercial" in license_lower
            or "non-commercial" in license_lower
            or "no derivatives" in license_lower
            or "noderivatives" in license_lower
            or bool(re.search(r"(?:^|[-\s])(?:nc|nd)(?:[-\s]|$)", license_lower))
        )
        if not license_name or restricted_license:
            continue
        if not any(allowed.lower() in license_lower for allowed in ALLOWED_LICENSES):
            continue
        description = re.sub(r"<[^>]+>", " ", str(metadata.get("ImageDescription", {}).get("value", "")))
        description = " ".join(unescape(description).split())
        title_terms = set(re.findall(r"[a-z0-9]{3,}", title.lower()))
        description_terms = set(re.findall(r"[a-z0-9]{3,}", description.lower()))
        matched_terms = set(topic_terms) & (title_terms | description_terms)
        if not matched_terms:
            continue
        try:
            size = int(info.get("size", 0) or 0)
        except (TypeError, ValueError):
            size = 0
        if size <= 0 or size > MAX_VIDEO_BYTES:
            continue
        # Rank files by topic overlap, preferring specific matches over generic B-roll.
        score = len(set(topic_terms) & title_terms) * 3 + len(set(topic_terms) & description_terms)
        results.append({
            "title": title,
            "url": url,
            "license": license_name,
            "artist": re.sub(r"<[^>]+>", " ", str(metadata.get("Artist", {}).get("value", "Unknown"))).strip() or "Unknown",
            "page": str(info.get("descriptionurl") or ("https://commons.wikimedia.org/wiki/" + quote(title.replace(" ", "_")))),
            "size": size,
            "_relevance": score,
            "_matched_query": matched_query,
        })
    results.sort(key=lambda item: item["_relevance"], reverse=True)
    for item in results:
        item.pop("_relevance", None)
        item.pop("_matched_query", None)
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
        narration = _script(topic, usable_sources, facts, client)
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
