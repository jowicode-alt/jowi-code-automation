from app.content import build_short_plan
from app.news_monitor import parse_feed, _similarity


def test_category_planner_keeps_storytelling_only_for_money_and_psychology():
    money = build_short_plan("Why habits shape wealth", category="money_success")
    psychology = build_short_plan("Why people procrastinate", category="psychology")
    comedy = build_short_plan("When the meeting could have been an email", category="comedy")
    tech = build_short_plan("A practical AI workflow", category="ai_technology")
    news = build_short_plan("Example international development", category="breaking_news")

    assert money["category"] == "money_success"
    assert psychology["category"] == "psychology"
    assert "story" not in comedy["presentation"].lower()
    assert "screen" in tech["presentation"].lower()
    assert news["requires_source_review"] is True
    assert news["source_review_ready"] is False
    assert all(len(plan["scenes"]) == 4 for plan in (money, psychology, comedy, tech, news))
    assert all(plan["publishing_enabled"] is False for plan in (money, psychology, comedy, tech, news))


def test_rss_parser_handles_rss_and_atom_links():
    rss = """<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>Example international story</title>
      <link>https://news.example/story</link>
      <pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate>
    </item></channel></rss>"""
    atom = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <title>Example Atom story</title>
      <link rel="alternate" href="https://atom.example/story" />
      <updated>2026-10-14T10:00:00Z</updated>
    </entry></feed>"""
    rss_items = parse_feed(rss, "Example RSS", "https://news.example/rss")
    atom_items = parse_feed(atom, "Example Atom", "https://atom.example/rss")
    assert rss_items[0]["url"] == "https://news.example/story"
    assert atom_items[0]["url"] == "https://atom.example/story"
    assert rss_items[0]["source"] == "Example RSS"


def test_news_title_similarity_requires_shared_specific_terms():
    assert _similarity(
        "Major earthquake damages buildings in coastal Japan",
        "Earthquake damages buildings across coastal Japan",
    ) >= 0.34
    assert _similarity(
        "Major earthquake damages buildings in coastal Japan",
        "Football club wins regional championship",
    ) < 0.34
