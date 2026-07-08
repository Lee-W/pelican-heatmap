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
    "most_active_day": "2025-03-01"
  }
"""

import json
import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

from pelican.generators import ArticlesGenerator

from pelican import signals  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class ArticleEntry(TypedDict):
    title: str
    url: str


class DayEntry(TypedDict):
    count: int
    articles: list[ArticleEntry]


def _get_article_generator(generators):
    """Return the first ArticlesGenerator found in generators, or None."""
    return next((g for g in generators if isinstance(g, ArticlesGenerator)), None)


def _article_url(article_url: str, siteurl: str) -> str:
    path = "/" + article_url.lstrip("/")
    return f"{siteurl.rstrip('/')}{path}" if siteurl else path


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


def generate_heatmap(generators) -> None:
    article_generator = _get_article_generator(generators)
    if article_generator is None:
        return

    date_articles: defaultdict[str, list[ArticleEntry]] = defaultdict(list)
    siteurl = str(article_generator.settings.get("SITEURL", ""))
    for article in article_generator.articles:
        day_str = article.date.date().isoformat()
        date_articles[day_str].append(
            {
                "title": article.title,
                "url": _article_url(article.url, siteurl),
            }
        )

    data: dict[str, DayEntry] = {
        day: {
            "count": len(articles),
            "articles": articles,
        }
        for day, articles in sorted(date_articles.items())
    }

    total = sum(v["count"] for v in data.values())
    most_active_day = max(data, key=lambda d: data[d]["count"]) if data else ""

    payload = {
        "data": data,
        "total": total,
        "most_active_day": most_active_day,
    }

    output_path = Path(article_generator.output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "writing-heatmap.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("[writing_heatmap] generated writing-heatmap.json (%d articles)", total)


def register() -> None:
    signals.all_generators_finalized.connect(generate_heatmap)
    signals.all_generators_finalized.connect(copy_static)
