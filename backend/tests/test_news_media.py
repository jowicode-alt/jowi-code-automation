from app.news_media import _ArticleText, _script


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
