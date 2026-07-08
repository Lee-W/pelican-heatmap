import json
import os
import tempfile
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

# Import the functions we want to test directly (no Pelican runtime needed)
from pelican.plugins.heatmap.heatmap import (
    copy_static,
    generate_heatmap,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_article(title: str, url: str, date_str: str):
    """Return a minimal mock article object."""
    d = date.fromisoformat(date_str)
    # Pelican article.date is a datetime; strftime must work, so we use a real date
    from datetime import datetime

    dt = datetime(d.year, d.month, d.day)
    return SimpleNamespace(title=title, url=url.lstrip("/"), date=dt)


def make_generators(
    articles: Sequence[Any], output_path: str, settings: dict[str, Any] | None = None
) -> list[Any]:
    """Return a minimal mock generators list (as all_generators_finalized provides)."""
    from pelican.generators import ArticlesGenerator

    # Subclass to avoid ArticlesGenerator's heavy __init__
    class MockArticlesGenerator(ArticlesGenerator):  # type: ignore[misc]
        def __init__(self) -> None:
            pass

    g = MockArticlesGenerator()
    g.articles = articles
    g.output_path = output_path
    g.settings = settings or {}
    return [g]


def run_generate(
    articles: Sequence[Any], settings: dict[str, Any] | None = None
) -> dict:
    """Run generate_heatmap and return the parsed JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        generators = make_generators(articles, tmpdir, settings)
        generate_heatmap(generators)
        json_path = os.path.join(tmpdir, "writing-heatmap.json")
        with open(json_path) as f:
            return cast(dict, json.load(f))


# ── JSON output: structure ────────────────────────────────────────────────────


class TestJSONStructure:
    def test_top_level_keys(self):
        articles = [make_article("A", "/a/", "2025-01-01")]
        out = run_generate(articles)
        assert set(out.keys()) == {
            "data",
            "total",
            "most_active_day",
        }

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


# ── Paths and static assets ───────────────────────────────────────────────────


class TestPathsAndAssets:
    def test_article_url_uses_siteurl_subpath(self):
        articles = [make_article("A", "posts/a.html", "2025-01-01")]
        out = run_generate(articles, {"SITEURL": "/blog"})
        assert out["data"]["2025-01-01"]["articles"][0]["url"] == "/blog/posts/a.html"

    def test_article_url_uses_absolute_siteurl(self):
        articles = [make_article("A", "/posts/a.html", "2025-01-01")]
        out = run_generate(articles, {"SITEURL": "https://example.com/blog/"})
        assert (
            out["data"]["2025-01-01"]["articles"][0]["url"]
            == "https://example.com/blog/posts/a.html"
        )

    def test_copy_static_writes_assets_to_documented_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            generators = make_generators([], tmpdir)
            copy_static(generators)

            output_static = Path(tmpdir) / "static" / "heatmap"
            assert (output_static / "pelican_heatmap.css").is_file()
            assert (output_static / "pelican_heatmap.js").is_file()
