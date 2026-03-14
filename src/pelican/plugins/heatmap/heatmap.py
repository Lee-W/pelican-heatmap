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
from collections import defaultdict
from datetime import date, timedelta

from pelican.generators import ArticlesGenerator

from pelican import signals


def generate_heatmap(generators):
    article_generator = next(
        (g for g in generators if isinstance(g, ArticlesGenerator)), None
    )
    if article_generator is None:
        return

    date_articles = defaultdict(list)
    for article in article_generator.articles:
        day_str = article.date.strftime("%Y-%m-%d")
        date_articles[day_str].append(
            {
                "title": article.title,
                "url": f"/{article.url}",
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

    payload = {
        "data": data,
        "total": total,
        "streak": streak,
        "most_active_day": most_active_day,
    }

    os.makedirs(article_generator.output_path, exist_ok=True)
    output_path = os.path.join(article_generator.output_path, "writing-heatmap.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[writing_heatmap] generated writing-heatmap.json ({total} articles)")


def _calculate_streak(data: dict) -> int:
    today = date.today()
    streak = 0

    start = today if today.strftime("%Y-%m-%d") in data else today - timedelta(days=1)
    current = start

    while True:
        key = current.strftime("%Y-%m-%d")
        if key in data:
            streak += 1
            current -= timedelta(days=1)
        else:
            break

    return streak


def register():
    signals.all_generators_finalized.connect(generate_heatmap)
