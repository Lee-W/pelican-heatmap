import json
import os
import tempfile
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

# Import the functions we want to test directly (no Pelican runtime needed)
from pelican.plugins.heatmap.heatmap import _calculate_streak, generate_heatmap

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_article(title: str, url: str, date_str: str):
    """Return a minimal mock article object."""
    d = date.fromisoformat(date_str)
    # Pelican article.date is a datetime; strftime must work, so we use a real date
    from datetime import datetime

    dt = datetime(d.year, d.month, d.day)
    return SimpleNamespace(title=title, url=url.lstrip("/"), date=dt)


def make_generators(articles: list, output_path: str):
    """Return a minimal mock generators list (as all_generators_finalized provides)."""
    from pelican.generators import ArticlesGenerator

    # Subclass to avoid ArticlesGenerator's heavy __init__
    class MockArticlesGenerator(ArticlesGenerator):
        def __init__(self):
            pass

    g = MockArticlesGenerator()
    g.articles = articles
    g.output_path = output_path
    return [g]


def run_generate(articles: list) -> dict:
    """Run generate_heatmap and return the parsed JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        generators = make_generators(articles, tmpdir)
        generate_heatmap(generators)
        json_path = os.path.join(tmpdir, "writing-heatmap.json")
        with open(json_path) as f:
            return json.load(f)


# ── JSON output: structure ────────────────────────────────────────────────────


class TestJSONStructure:
    def test_top_level_keys(self):
        articles = [make_article("A", "/a/", "2025-01-01")]
        out = run_generate(articles)
        assert set(out.keys()) == {"data", "total", "streak", "most_active_day"}

    def test_data_entry_keys(self):
        articles = [make_article("A", "/a/", "2025-01-01")]
        out = run_generate(articles)
        entry = out["data"]["2025-01-01"]
        assert set(entry.keys()) == {"count", "articles"}

    def test_article_entry_keys(self):
        articles = [make_article("Hello", "/hello/", "2025-03-10")]
        out = run_generate(articles)
        article = out["data"]["2025-03-10"]["articles"][0]
        assert set(article.keys()) == {"title", "url"}

    def test_url_has_leading_slash(self):
        articles = [make_article("A", "posts/a.html", "2025-01-01")]
        out = run_generate(articles)
        assert out["data"]["2025-01-01"]["articles"][0]["url"].startswith("/")

    def test_no_articles_produces_empty_json(self):
        out = run_generate([])
        assert out["total"] == 0
        assert out["data"] == {}
        assert out["streak"] == 0

    def test_output_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "nested", "output")
            articles = [make_article("A", "/a/", "2025-01-01")]
            generators = make_generators(articles, output_path)
            generate_heatmap(generators)
            assert os.path.exists(os.path.join(output_path, "writing-heatmap.json"))


# ── JSON output: counts and totals ───────────────────────────────────────────


class TestCounts:
    def test_single_article(self):
        articles = [make_article("A", "/a/", "2025-06-01")]
        out = run_generate(articles)
        assert out["data"]["2025-06-01"]["count"] == 1
        assert out["total"] == 1

    def test_multiple_articles_same_day(self):
        articles = [
            make_article("A", "/a/", "2025-06-01"),
            make_article("B", "/b/", "2025-06-01"),
            make_article("C", "/c/", "2025-06-01"),
        ]
        out = run_generate(articles)
        assert out["data"]["2025-06-01"]["count"] == 3
        assert out["total"] == 3

    def test_articles_across_multiple_days(self):
        articles = [
            make_article("A", "/a/", "2025-01-01"),
            make_article("B", "/b/", "2025-01-03"),
            make_article("C", "/c/", "2025-01-03"),
        ]
        out = run_generate(articles)
        assert out["data"]["2025-01-01"]["count"] == 1
        assert out["data"]["2025-01-03"]["count"] == 2
        assert out["total"] == 3

    def test_data_keys_are_sorted(self):
        articles = [
            make_article("C", "/c/", "2025-03-01"),
            make_article("A", "/a/", "2025-01-01"),
            make_article("B", "/b/", "2025-02-01"),
        ]
        out = run_generate(articles)
        keys = list(out["data"].keys())
        assert keys == sorted(keys)

    def test_most_active_day(self):
        articles = [
            make_article("A", "/a/", "2025-01-01"),
            make_article("B", "/b/", "2025-02-01"),
            make_article("C", "/c/", "2025-02-01"),
        ]
        out = run_generate(articles)
        assert out["most_active_day"] == "2025-02-01"

    def test_article_order_preserved_within_day(self):
        articles = [
            make_article("First", "/first/", "2025-05-01"),
            make_article("Second", "/second/", "2025-05-01"),
        ]
        out = run_generate(articles)
        titles = [a["title"] for a in out["data"]["2025-05-01"]["articles"]]
        assert titles == ["First", "Second"]


# ── Streak calculation ────────────────────────────────────────────────────────


class TestStreak:
    """
    _calculate_streak() is tested in isolation with a fixed 'today' via mock,
    so results are deterministic regardless of when the tests run.
    """

    def _run(self, data: dict, today_str: str) -> int:
        today = date.fromisoformat(today_str)
        with patch("pelican.plugins.heatmap.heatmap.date") as mock_date:
            mock_date.today.return_value = today
            mock_date.fromisoformat = date.fromisoformat
            return _calculate_streak(data)

    def test_no_posts_streak_is_zero(self):
        assert self._run({}, "2025-06-10") == 0

    def test_only_today(self):
        data = {"2025-06-10": {"count": 1, "articles": []}}
        assert self._run(data, "2025-06-10") == 1

    def test_only_yesterday(self):
        data = {"2025-06-09": {"count": 1, "articles": []}}
        assert self._run(data, "2025-06-10") == 1

    def test_today_and_yesterday(self):
        data = {
            "2025-06-09": {"count": 1, "articles": []},
            "2025-06-10": {"count": 1, "articles": []},
        }
        assert self._run(data, "2025-06-10") == 2

    def test_consecutive_days_not_including_today(self):
        data = {
            "2025-06-07": {"count": 1, "articles": []},
            "2025-06-08": {"count": 1, "articles": []},
            "2025-06-09": {"count": 1, "articles": []},
        }
        assert self._run(data, "2025-06-10") == 3

    def test_streak_broken_by_gap(self):
        data = {
            "2025-06-05": {"count": 1, "articles": []},
            # gap on 06-06
            "2025-06-07": {"count": 1, "articles": []},
            "2025-06-08": {"count": 1, "articles": []},
            "2025-06-09": {"count": 1, "articles": []},
        }
        # streak from yesterday backward: 09, 08, 07 → 3 (stops at gap)
        assert self._run(data, "2025-06-10") == 3

    def test_old_posts_dont_count_if_gap_before_yesterday(self):
        data = {
            "2025-01-01": {"count": 1, "articles": []},
            "2025-01-02": {"count": 1, "articles": []},
        }
        # today is 2025-06-10, yesterday is 06-09 — no post → streak 0
        assert self._run(data, "2025-06-10") == 0

    def test_streak_across_month_boundary(self):
        data = {
            "2025-05-30": {"count": 1, "articles": []},
            "2025-05-31": {"count": 1, "articles": []},
            "2025-06-01": {"count": 1, "articles": []},
        }
        assert self._run(data, "2025-06-01") == 3

    def test_streak_across_year_boundary(self):
        data = {
            "2024-12-30": {"count": 1, "articles": []},
            "2024-12-31": {"count": 1, "articles": []},
            "2025-01-01": {"count": 1, "articles": []},
        }
        assert self._run(data, "2025-01-01") == 3

    def test_today_not_written_uses_yesterday_as_start(self):
        # yesterday and day before — no post today
        data = {
            "2025-06-08": {"count": 1, "articles": []},
            "2025-06-09": {"count": 1, "articles": []},
        }
        assert self._run(data, "2025-06-10") == 2

    def test_single_post_two_days_ago_is_zero(self):
        data = {"2025-06-08": {"count": 1, "articles": []}}
        # yesterday (06-09) is missing → streak breaks immediately
        assert self._run(data, "2025-06-10") == 0
