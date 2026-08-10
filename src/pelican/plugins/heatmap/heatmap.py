"""
output format:
  {
    "data": {
      "2025-01-03": {
        "count": 2,
        "articles": [
          { "title": "文章標題", "url": "/path/to/article.html" },
          ...
        ]
      },
      ...
    },
    "total": 42,
    "most_active_day": "2025-03-01",
    "week_start": 0
  }
"""

import json
import logging
import re
import shutil
from collections import defaultdict
from collections.abc import Mapping
from html import escape
from pathlib import Path
from typing import TypedDict

from pelican.contents import Content
from pelican.generators import ArticlesGenerator

from pelican import Pelican, signals  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_WEEK_START = 0
HEATMAP_SHORTCODE = re.compile(r"<p>\s*\{%\s+heatmap\s+%\}\s*</p>")


class ArticleEntry(TypedDict):
    title: str
    url: str


class DayEntry(TypedDict):
    count: int
    articles: list[ArticleEntry]


# --- Cross-round accumulation (fixes the "298 instead of 322" bug) --------
#
# This is the SAME problem `pelican-stat`'s `pelican_stat/plugin.py`
# (`_ACCUMULATED_ARTICLES` / `_ACCUMULATION_DEPTH`) solves, and this module
# copies that pattern's *shape* (depth counting, only reset once depth
# unwinds to 0, mutate the accumulator in place) rather than importing it --
# see `main-blog` repo's `.maigo/plan.md` Milestone C, "設計判斷 5" for the
# full "share vs duplicate" trade-off write-up. The two plugins deliberately
# do NOT depend on each other: the target data shape here (a day -> articles
# bucket, not a single aggregate dict) is different enough that a shared
# helper would either be a leaky one-off abstraction or force an unwanted
# inter-package dependency between two independently-released plugins.
#
# `article_generator.articles` on ANY single `all_generators_finalized`
# call is only that round's language build (298 zh on the primary call, 24
# en on the nested `i18n_subsites` call) -- never the full site. Both
# `all_generators_finalized` calls happen before EITHER round's
# `generate_output()` renders a single page (confirmed by reading
# `pelican.Pelican.run()`/`_get_writer()`; same timeline `pelican-stat`
# documents). Each round's own `SITEURL` must be used to build that round's
# article URLs *at accumulation time* -- caching bare `Article` objects and
# converting URLs later with a single `SITEURL` would silently break the
# links for whichever language didn't "win" that later conversion.
#
# `_KNOWN_OUTPUT_PATHS` records every round's own `output_path` (`output/`
# for the primary zh build, `output/en/` for the nested en subsite) together
# with that round's `HEATMAP_WEEK_START`. The JSON file is (re)written to
# *every* known output path on every round --
# wasteful on early rounds (they only have partial data) but correct: the
# very last round to fire `all_generators_finalized` (guaranteed, by the
# same timeline argument, to happen before any `generate_output()` in the
# whole build tree) always rewrites every known path with the final,
# fully-accumulated data, overwriting any earlier partial writes.
_ACCUMULATED_DATE_ARTICLES: defaultdict[str, list[ArticleEntry]] = defaultdict(list)
_SEEN_SOURCE_PATHS: set[str] = set()
_KNOWN_OUTPUT_PATHS: dict[str, int] = {}
_ACCUMULATION_DEPTH = 0


def _get_article_generator(generators):
    """Return the first ArticlesGenerator found in generators, or None."""
    return next((g for g in generators if isinstance(g, ArticlesGenerator)), None)


def _article_url(article_url: str, siteurl: str) -> str:
    path = "/" + article_url.lstrip("/")
    return f"{siteurl.rstrip('/')}{path}" if siteurl else path


def _shortcode_html(siteurl: str) -> str:
    """Return the complete widget markup for a content shortcode."""
    base_url = siteurl.rstrip("/")
    stylesheet_url = escape(
        f"{base_url}/static/heatmap/pelican_heatmap.css", quote=True
    )
    data_url = escape(f"{base_url}/writing-heatmap.json", quote=True)
    script_url = escape(f"{base_url}/static/heatmap/pelican_heatmap.js", quote=True)

    return "\n".join(
        (
            f'<link rel="stylesheet" href="{stylesheet_url}">',
            f'<div id="writing-heatmap" data-src="{data_url}"></div>',
            f'<script src="{script_url}" defer></script>',
        )
    )


def expand_heatmap_shortcode(content_object: Content) -> None:
    """Expand a standalone ``{% heatmap %}`` paragraph in parsed content."""
    matches = list(HEATMAP_SHORTCODE.finditer(content_object._content))
    if not matches:
        return

    siteurl = str(content_object.settings.get("SITEURL", ""))
    widget_html = _shortcode_html(siteurl)
    rendered = False

    def replace_shortcode(_match: re.Match[str]) -> str:
        nonlocal rendered
        if rendered:
            return ""
        rendered = True
        return widget_html

    content_object._content = HEATMAP_SHORTCODE.sub(
        replace_shortcode, content_object._content
    )

    if len(matches) > 1:
        logger.warning(
            "[writing_heatmap] %s contains %d heatmap shortcodes; only the first "
            "was rendered",
            content_object.source_path,
            len(matches),
        )


def _week_start(settings: Mapping[str, object]) -> int:
    value = settings.get("HEATMAP_WEEK_START", DEFAULT_WEEK_START)
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 6:
        return value

    logger.warning(
        "[writing_heatmap] invalid HEATMAP_WEEK_START %r; using %d",
        value,
        DEFAULT_WEEK_START,
    )
    return DEFAULT_WEEK_START


def copy_static(generators) -> None:
    """Copy CSS and JS to output/static/heatmap/."""
    article_generator = _get_article_generator(generators)
    if article_generator is None:
        return

    dest = Path(article_generator.output_path) / "static" / "heatmap"
    dest.mkdir(parents=True, exist_ok=True)

    for f in STATIC_DIR.iterdir():
        if f.suffix in (".css", ".js"):
            shutil.copy2(f, dest / f.name)

    logger.debug("[writing_heatmap] copied static assets to %s", dest)


def _write_heatmap_json() -> None:
    """Write the currently-accumulated data to every known output path.

    Called on every round (see module docstring above): early rounds only
    have partial data, but the last round before any `generate_output()`
    always rewrites every known path with the final, fully-accumulated
    data.
    """
    data: dict[str, DayEntry] = {
        day: {
            "count": len(articles),
            "articles": articles,
        }
        for day, articles in sorted(_ACCUMULATED_DATE_ARTICLES.items())
    }

    total = sum(v["count"] for v in data.values())
    most_active_day = max(data, key=lambda d: data[d]["count"]) if data else ""

    base_payload = {
        "data": data,
        "total": total,
        "most_active_day": most_active_day,
    }

    for known_output_path, week_start in _KNOWN_OUTPUT_PATHS.items():
        payload = {**base_payload, "week_start": week_start}
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        output_path = Path(known_output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "writing-heatmap.json").write_text(
            payload_json, encoding="utf-8"
        )

    logger.info("[writing_heatmap] generated writing-heatmap.json (%d articles)", total)


def generate_heatmap(generators) -> None:
    global _ACCUMULATION_DEPTH

    _ACCUMULATION_DEPTH += 1

    article_generator = _get_article_generator(generators)
    if article_generator is None:
        return

    siteurl = str(article_generator.settings.get("SITEURL", ""))
    _KNOWN_OUTPUT_PATHS[str(article_generator.output_path)] = _week_start(
        article_generator.settings
    )

    for article in article_generator.articles:
        source_path = str(article.source_path)
        if source_path in _SEEN_SOURCE_PATHS:
            # Already accumulated in an earlier round -- e.g. a
            # `livereload`/`--autoreload` rebuild that crashed mid-way
            # left the accumulator un-reset (see `_reset_accumulator`
            # below). Skipping here keeps the totals from inflating past
            # the true site-wide article count.
            continue
        _SEEN_SOURCE_PATHS.add(source_path)

        day_str = article.date.date().isoformat()
        _ACCUMULATED_DATE_ARTICLES[day_str].append(
            {
                "title": article.title,
                # Computed with THIS round's own SITEURL, right now --
                # not deferred and converted later with some other
                # round's SITEURL. See module docstring above.
                "url": _article_url(article.url, siteurl),
            }
        )

    _write_heatmap_json()


def _reset_accumulator(pelican_instance: Pelican | None) -> None:
    """Reset the module-level accumulator once the outermost `Pelican.run()` finishes.

    Mirrors `pelican_stat.plugin._reset_word_count_cache`'s depth-tracking
    reasoning: `signals.finalized` fires once per `all_generators_finalized`
    (including once for the nested en subsite build), and the nested
    `finalized` fires before the primary/outer site's own
    `generate_output()` has rendered anything yet. Only reset once
    `_ACCUMULATION_DEPTH` unwinds back to 0 -- the outermost, last
    `finalized` of this whole `Pelican.run()` tree -- so a still-pending
    outer round never has its data wiped out from under it.
    """
    global _ACCUMULATION_DEPTH

    _ACCUMULATION_DEPTH -= 1
    if _ACCUMULATION_DEPTH > 0:
        return

    _ACCUMULATION_DEPTH = 0  # defensive: never let depth go negative
    _ACCUMULATED_DATE_ARTICLES.clear()
    _SEEN_SOURCE_PATHS.clear()
    _KNOWN_OUTPUT_PATHS.clear()


def _reset_accumulator_for_testing() -> None:
    """Unconditionally reset the module-level accumulator.

    Test-only helper, not part of the public API.
    """
    global _ACCUMULATION_DEPTH
    _ACCUMULATION_DEPTH = 0
    _ACCUMULATED_DATE_ARTICLES.clear()
    _SEEN_SOURCE_PATHS.clear()
    _KNOWN_OUTPUT_PATHS.clear()


def register() -> None:
    signals.content_object_init.connect(expand_heatmap_shortcode)
    signals.all_generators_finalized.connect(generate_heatmap)
    signals.all_generators_finalized.connect(copy_static)
    signals.finalized.connect(_reset_accumulator)
