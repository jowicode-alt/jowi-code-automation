import pytest

from app.news_media import COMMONS_API, USER_AGENT, _ArticleText, _script, _video_results


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _FakeHorde:
    def post(self, *args, **kwargs):
        assert "/v2/generate/text/async" in args[0]
        return _Response({"id": "test-request"})

    def get(self, *args, **kwargs):
        assert "/v2/generate/text/status/test-request" in args[0]
        narration = (
            "Here is the developing story with details confirmed by two independent reports. "
            "Officials have described the event and provided additional context for the public. "
            "The reports explain what happened, while several important details remain unconfirmed. "
            "The information available now may change as more reliable reporting becomes available. "
            "People should consult the original sources before drawing conclusions about the situation. "
            "Further updates should be checked directly with the reporting organizations. "
            "Subscribe to The Jowi Code for clear, sourced news. Thanks for watching."
        )
        return _Response({"generations": [{"text": narration}]})


def test_article_parser_collects_real_paragraph_text():
    parser = _ArticleText()
    paragraph = "Officials provided additional information about the developing event and described what is currently known. "
    parser.feed(f"<html><title>News report</title><p>{paragraph * 2}</p></html>")
    assert parser.paragraphs
    assert "Officials provided additional information" in parser.paragraphs[0]


def test_news_script_uses_free_ai_horde_and_requires_signoff(monkeypatch):
    monkeypatch.setenv("AI_HORDE_API_KEY", "0000000000")
    sources = [
        {"source": "Publisher A", "url": "https://example.com/a", "facts": ["Fact one from a report."]},
        {"source": "Publisher B", "url": "https://example.com/b", "facts": ["Fact two from a report."]},
    ]
    narration = _script("Test event", sources, ["fact one", "fact two", "fact three"], _FakeHorde())
    assert len(narration.split()) >= 75
    assert "The Jowi Code" in narration
    assert "Thanks for watching" in narration



class _RejectedThenAnonymousHorde(_FakeHorde):
    def __init__(self):
        self.keys = []

    def post(self, *args, **kwargs):
        self.keys.append(kwargs["headers"]["apikey"])
        if len(self.keys) == 1:
            return _Response({"message": "credential rejected"}, status_code=403)
        return _Response({"id": "test-request"}, status_code=200)


def test_news_script_retries_once_with_anonymous_key_after_403(monkeypatch):
    monkeypatch.setenv("AI_HORDE_API_KEY", "configured-key")
    horde = _RejectedThenAnonymousHorde()
    sources = [
        {"source": "Publisher A", "url": "https://example.com/a", "facts": ["Fact one from a report."]},
        {"source": "Publisher B", "url": "https://example.com/b", "facts": ["Fact two from a report."]},
    ]
    narration = _script("Test event", sources, ["fact one", "fact two", "fact three"], horde)
    assert len(narration.split()) >= 75
    assert horde.keys == ["configured-key", "0000000000"]



class _AlwaysForbiddenHorde(_FakeHorde):
    def __init__(self):
        self.keys = []

    def post(self, *args, **kwargs):
        self.keys.append(kwargs["headers"]["apikey"])
        return _Response({"message": "access forbidden"}, status_code=403)


def test_news_script_uses_sourced_fallback_if_both_horde_keys_are_forbidden(monkeypatch):
    monkeypatch.setenv("AI_HORDE_API_KEY", "configured-key")
    horde = _AlwaysForbiddenHorde()
    sources = [
        {"source": "Publisher A", "url": "https://example.com/a", "facts": ["Officials confirmed the city centre reopened after the overnight emergency response."]},
        {"source": "Publisher B", "url": "https://example.com/b", "facts": ["A separate report says local authorities are continuing their investigation today."]},
    ]
    narration = _script("Test event", sources, ["fact one", "fact two", "fact three"], horde)
    assert "Publisher A reports" in narration
    assert "A separate report from Publisher B" in narration
    assert "The Jowi Code" in narration
    assert "Thanks for watching" in narration
    assert horde.keys == ["configured-key", "0000000000"]



class _CommonsResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            request = httpx.Request("GET", COMMONS_API)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    def json(self):
        return {"query": {"pages": {}}}


class _CommonsClient:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.headers = None

    def get(self, url, **kwargs):
        assert url == COMMONS_API
        self.headers = kwargs.get("headers", {})
        return _CommonsResponse(self.status_code)


def test_commons_request_uses_descriptive_user_agent_with_contact_url():
    client = _CommonsClient()
    assert _video_results("ships near strait", client) == []
    assert client.headers["User-Agent"] == USER_AGENT
    assert "https://github.com/jowicode-alt/jowi-code-automation" in USER_AGENT
    assert "contact channel owner" not in USER_AGENT


def test_commons_403_is_reported_without_bypassing_access_denial():
    client = _CommonsClient(status_code=403)
    with pytest.raises(RuntimeError, match="Wikimedia Commons denied the API request"):
        _video_results("ships near strait", client)
