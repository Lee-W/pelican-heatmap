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
    _reset_accumulator_for_testing,
    copy_static,
    generate_heatmap,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_article(title: str, url: str, date_str: str, source_path: str | None = None):
    """Return a minimal mock article object.

    `source_path` defaults to `url` (unique per article in nearly every
    test); pass an explicit, identical `source_path` across two calls when a
    test wants to simulate "the same article appears in more than one
    round" (e.g. a crashed-then-rerun `livereload` accumulator).
    """
    d = date.fromisoformat(date_str)
    # Pelican article.date is a datetime; strftime must work, so we use a real date
    from datetime import datetime

    dt = datetime(d.year, d.month, d.day)
    return SimpleNamespace(
        title=title,
        url=url.lstrip("/"),
        date=dt,
        source_path=source_path if source_path is not None else url,
    )


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


def _read_json(output_path: str) -> dict:
    json_path = os.path.join(output_path, "writing-heatmap.json")
    with open(json_path) as f:
        return cast(dict, json.load(f))


def run_generate(
    articles: Sequence[Any], settings: dict[str, Any] | None = None
) -> dict:
    """Reset the accumulator, run a single fresh round, return the parsed JSON output.

    Resetting first keeps every pre-existing single-round test isolated
    from cross-round accumulation state left behind by other tests in this
    file (pytest-xdist runs this file's tests in one worker process via
    `--dist=loadfile`, so module-level state persists across tests unless
    explicitly cleared).
    """
    _reset_accumulator_for_testing()
    with tempfile.TemporaryDirectory() as tmpdir:
        generators = make_generators(articles, tmpdir, settings)
        generate_heatmap(generators)
        return _read_json(tmpdir)


# ── JSON output: structure ────────────────────────────────────────────────────


class TestJSONStructure:
    def test_top_level_keys(self):
        articles = [make_article("A", "/a/", "2025-01-01")]
        out = run_generate(articles)
        assert set(out.keys()) == {
            "data",
            "total",
            "most_active_day",
            "week_start",
        }

    def test_week_start_defaults_to_sunday(self):
        out = run_generate([])
        assert out["week_start"] == 0

    def test_week_start_uses_pelican_setting(self):
        out = run_generate([], {"HEATMAP_WEEK_START": 1})
        assert out["week_start"] == 1

    def test_invalid_week_start_falls_back_to_sunday(self):
        out = run_generate([], {"HEATMAP_WEEK_START": 7})
        assert out["week_start"] == 0

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

    def test_week_start_is_configurable_across_widget(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            generators = make_generators([], tmpdir)
            copy_static(generators)

            script = (
                Path(tmpdir) / "static" / "heatmap" / "pelican_heatmap.js"
            ).read_text(encoding="utf-8")

            assert "Number(json.week_start ?? 0)" in script
            assert "orderedDays.map" in script
            assert "weekStart.getDate() - daysFromWeekStart(weekStart)" in script
            assert "6 - daysFromWeekStart(base)" in script
            assert "cur.getDay() === weekStartDay" in script


# ── Cross-round accumulation (the 298-vs-322 bug) ───────────────────────────


class TestCrossRoundAccumulation:
    def test_two_rounds_accumulate_to_combined_total(self):
        """Simulates the primary (zh) round then the nested (en) subsite round."""
        _reset_accumulator_for_testing()
        with (
            tempfile.TemporaryDirectory() as primary_dir,
            tempfile.TemporaryDirectory() as nested_dir,
        ):
            zh_articles = [
                make_article("Zh A", "/posts/zh-a/", "2025-01-01"),
                make_article("Zh B", "/posts/zh-b/", "2025-01-02"),
            ]
            en_articles = [
                make_article("En A", "/posts/en-a/", "2025-01-03"),
            ]

            generate_heatmap(
                make_generators(
                    zh_articles, primary_dir, {"SITEURL": "https://blog.example.com"}
                )
            )
            generate_heatmap(
                make_generators(
                    en_articles, nested_dir, {"SITEURL": "https://blog.example.com/en"}
                )
            )

            primary_out = _read_json(primary_dir)
            nested_out = _read_json(nested_dir)

            assert primary_out["total"] == 3
            assert nested_out["total"] == 3
            assert primary_out == nested_out

    def test_repeated_source_path_does_not_inflate_total(self):
        """Simulates a crashed livereload rebuild that left the accumulator un-reset."""
        _reset_accumulator_for_testing()
        with tempfile.TemporaryDirectory() as tmpdir:
            article = make_article(
                "A", "/posts/a/", "2025-01-01", source_path="content/a.md"
            )

            generate_heatmap(make_generators([article], tmpdir))
            # Same source_path reappears in a second round (e.g. leftover
            # accumulator state after a crashed rebuild) -- must not double count.
            generate_heatmap(make_generators([article], tmpdir))

            out = _read_json(tmpdir)
            assert out["total"] == 1
            assert out["data"]["2025-01-01"]["count"] == 1

    def test_each_round_url_uses_its_own_siteurl(self):
        """zh articles link to the primary site; en articles link under /en/."""
        _reset_accumulator_for_testing()
        with (
            tempfile.TemporaryDirectory() as primary_dir,
            tempfile.TemporaryDirectory() as nested_dir,
        ):
            zh_article = make_article("Zh A", "posts/zh-a.html", "2025-01-01")
            en_article = make_article("En A", "posts/en-a.html", "2025-01-02")

            generate_heatmap(
                make_generators(
                    [zh_article], primary_dir, {"SITEURL": "https://blog.example.com"}
                )
            )
            generate_heatmap(
                make_generators(
                    [en_article], nested_dir, {"SITEURL": "https://blog.example.com/en"}
                )
            )

            merged = _read_json(
                nested_dir
            )  # both output paths hold identical merged data
            zh_url = merged["data"]["2025-01-01"]["articles"][0]["url"]
            en_url = merged["data"]["2025-01-02"]["articles"][0]["url"]

            assert zh_url == "https://blog.example.com/posts/zh-a.html"
            assert "/en/" not in zh_url
            assert en_url == "https://blog.example.com/en/posts/en-a.html"

    def test_each_output_uses_its_own_week_start_setting(self):
        _reset_accumulator_for_testing()
        with (
            tempfile.TemporaryDirectory() as primary_dir,
            tempfile.TemporaryDirectory() as nested_dir,
        ):
            generate_heatmap(
                make_generators([], primary_dir, {"HEATMAP_WEEK_START": 0})
            )
            generate_heatmap(
                make_generators([], nested_dir, {"HEATMAP_WEEK_START": 1})
            )

            assert _read_json(primary_dir)["week_start"] == 0
            assert _read_json(nested_dir)["week_start"] == 1
