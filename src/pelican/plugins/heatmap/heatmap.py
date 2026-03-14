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
    "most_active_day": "2025-03-01"
  }
"""

import json
import os
import shutil
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from pelican import signals

STATIC_DIR = Path(__file__).parent / "static"


def copy_static(generator):
    dest = Path(generator.output_path) / "static"
    dest.mkdir(parents=True, exist_ok=True)
    for f in STATIC_DIR.iterdir():
        shutil.copy2(f, dest / f.name)


def generate_heatmap(generator):
    date_articles = defaultdict(list)
    for article in generator.articles:
        day_str = article.date.strftime("%Y-%m-%d")
        date_articles[day_str].append(
            {
                "title": article.title,
                "url": "/" + article.url,
            }
        )

    if not date_articles:
        return

    data = {
        day: {
            "count": len(articles),
            "articles": articles,
        }
        for day, articles in sorted(date_articles.items())
    }

    total = sum(v["count"] for v in data.values())
    most_active_day = max(data, key=lambda d: data[d]["count"])

    streak = _calculate_streak(data)
    payload = {
        "data": data,
        "total": total,
        "streak": streak,
        "most_active_day": most_active_day,
    }

    output_path = os.path.join(generator.output_path, "writing-heatmap.json")
    os.makedirs(generator.output_path, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[pelican_heatmap] Generate `writing-heatmap.json` with {total} articles")


def _calculate_streak(data: dict) -> int:
    today = date.today()
    streak = 0
    current = today

    while True:
        key = current.strftime("%Y-%m-%d")
        if key in data:
            streak += 1
            current -= timedelta(days=1)
        else:
            if current == today:
                current -= timedelta(days=1)
                continue
            break

    return streak


def register():
    signals.article_generator_finalized.connect(generate_heatmap)
    signals.finalized.connect(copy_static)
