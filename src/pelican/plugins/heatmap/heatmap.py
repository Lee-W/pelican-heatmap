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
    "streak": 5,
    "weekly_streak": 3,
    "most_active_day": "2025-03-01"
  }
"""

import json
import logging
import shutil
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from pelican.generators import ArticlesGenerator

from pelican import signals

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def _get_article_generator(generators):
    """Return the first ArticlesGenerator found in generators, or None."""
    return next((g for g in generators if isinstance(g, ArticlesGenerator)), None)


def copy_static(generators):
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


def generate_heatmap(generators):
    article_generator = _get_article_generator(generators)
    if article_generator is None:
        return

    date_articles = defaultdict(list)
    for article in article_generator.articles:
        day_str = article.date.date().isoformat()
        date_articles[day_str].append(
            {
                "title": article.title,
                "url": "/" + article.url,
            }
        )

    data = {
        day: {
            "count": len(articles),
            "articles": articles,
        }
        for day, articles in sorted(date_articles.items())
    }

    total = sum(v["count"] for v in data.values())
    most_active_day = max(data, key=lambda d: data[d]["count"]) if data else ""
    streak = _calculate_streak(data)
    weekly_streak = _calculate_weekly_streak(data)

    payload = {
        "data": data,
        "total": total,
        "streak": streak,
        "weekly_streak": weekly_streak,
        "most_active_day": most_active_day,
    }

    output_path = Path(article_generator.output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "writing-heatmap.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("[writing_heatmap] generated writing-heatmap.json (%d articles)", total)


def _calculate_streak(data: dict[str, dict]) -> int:
    today = date.today()
    streak = 0

    start = today if today.isoformat() in data else today - timedelta(days=1)
    current = start

    while True:
        key = current.isoformat()
        if key in data:
            streak += 1
            current -= timedelta(days=1)
        else:
            break

    return streak


def _calculate_weekly_streak(data: dict[str, dict]) -> int:
    today = date.today()
    streak = 0
    # Monday of the current ISO week
    week_start = today - timedelta(days=today.weekday())

    def week_has_posts(ws: date) -> bool:
        for i in range(7):
            day = ws + timedelta(days=i)
            if day > today:
                break
            if day.isoformat() in data:
                return True
        return False

    if not week_has_posts(week_start):
        week_start -= timedelta(weeks=1)

    while week_has_posts(week_start):
        streak += 1
        week_start -= timedelta(weeks=1)

    return streak


def register():
    signals.all_generators_finalized.connect(generate_heatmap)
    signals.all_generators_finalized.connect(copy_static)
