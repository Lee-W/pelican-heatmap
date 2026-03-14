# pelican-heatmap

A [Pelican](https://getpelican.com) plugin that generates a GitHub-style writing activity heatmap for your blog. At build time it scans all your articles and produces a JSON data file; a self-contained JS + CSS widget reads that file and renders an interactive calendar you can drop into any page.

---

## Features

- **GitHub-style heatmap** — one cell per day, four color levels based on post frequency
- **Year navigation** — scroll back through your entire writing history with ‹ › buttons; the view always opens on the most recent year
- **Live stats** — posts in the current view window, all-time total, and current streak
- **Clickable cells** — click any day to pin a tooltip listing that day's articles with links; click again to dismiss
- **Dark mode** — respects `prefers-color-scheme` automatically
- **i18n** — all UI strings are overridable via `window.HM_LOCALE`
- **Customizable** — every element has a named CSS class and the color palette is controlled by CSS custom properties
- **Zero dependencies** — no third-party libraries required

## Installation

```bash
pip install pelican-heatmap
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add pelican-heatmap
```

## Setup

### 1. Enable the plugin

```python
# pelicanconf.py
PLUGINS = ["pelican.plugins.heatmap"]
```

### 2. Add the widget to a page

The plugin copies `pelican_heatmap.css` and `pelican_heatmap.js` to `output/static/` automatically at build time. Add these three lines wherever you want the heatmap to appear — a dedicated page, your about page, or a sidebar:

```html
<link rel="stylesheet" href="/static/pelican_heatmap.css">
<div id="writing-heatmap"></div>
<script src="/static/pelican_heatmap.js" defer></script>
```

In a Jinja2 template:

```html
<link rel="stylesheet" href="{{ SITEURL }}/static/pelican_heatmap.css">
<div id="writing-heatmap"></div>
<script src="{{ SITEURL }}/static/pelican_heatmap.js" defer></script>
```

### 3. Build

```bash
pelican content
```

The plugin generates `output/writing-heatmap.json` and copies the static assets. That's it.

---

## Localization

Override any UI string by setting `window.HM_LOCALE` **before** the script loads:

```html
<script>
window.HM_LOCALE = {
  months:    ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'],
  days:      ['日','一','二','三','四','五','六'],
  less:      '少',
  more:      '多',
  no_posts:  '無文章',
  posts:     '篇',
  alltime:   '累計\n篇數',
  streak:    '連續\n天數',
  prev_year: '往前一年',
  next_year: '往後一年',
};
</script>
<script src="/static/writing_heatmap.js" defer></script>
```

All keys are optional — omitted keys fall back to the English defaults.

---

## Customization

### CSS custom properties

Override these in `:root` or any parent selector:

| Property | Default (light) | Description |
| --- | --- | --- |
| `--hm-cell-size` | `14px` | Cell and row height; scales the whole grid |
| `--hm-cell-empty` | `#e8e6e1` | Empty cell color |
| `--hm-card-bg` | `#f0ede8` | Stat card background |
| `--hm-text-num` | `#1a1a1a` | Large number color |
| `--hm-text-muted` | `#888` | Label and secondary text |
| `--hm-label-col` | `#aaa` | Month and legend label color |
| `--hm-label-day` | `#bbb` | Weekday label color |
| `--hm-btn-bg` | `#ede9e3` | Nav button background |
| `--hm-btn-hover` | `#ddd9d2` | Nav button hover background |
| `--hm-btn-text` | `#555` | Nav button text |
| `--hm-btn-dis` | `#ccc` | Disabled button text |

Example — larger cells:

```css
#writing-heatmap {
  --hm-cell-size: 18px;
}
```

### Color levels

```css
.hm-cell[data-level="1"] { background: #a8c8f8; }
.hm-cell[data-level="2"] { background: #5a9fd4; }
.hm-cell[data-level="3"] { background: #2376b7; }
.hm-cell[data-level="4"] { background: #0d4f8a; }
```

### Full class reference

```css
#writing-heatmap               outer wrapper
.hm-stats                      stats row
.hm-stat-card                  individual stat card
.hm-stat-num                   large number in card
.hm-stat-label                 label below number
.hm-nav                        nav row
.hm-nav-btn                    prev / next buttons
.hm-nav-range                  date range text
.hm-container                  scrollable grid wrapper
.hm-month-label-cell           per-column month span
.hm-month-label-cell--visible  span showing a month name
.hm-day-labels                 Su Mo … Sa column
.hm-grid                       the cell grid
.hm-cell                       individual day cell
.hm-cell[data-level="0–4"]     color levels
.hm-cell--future               days after today
.hm-cell--past                 days before first article
.hm-legend                     legend row
.hm-legend-cell                legend color swatch
.hm-tooltip                    tooltip container
.hm-tooltip.hm-visible         tooltip when shown (hover)
.hm-tooltip.hm-pinned          tooltip when clicked / pinned
.hm-tt-date                    date line inside tooltip
.hm-tt-list                    article list inside tooltip
.hm-tt-empty                   "No posts" message
```

---

## JSON format

The plugin writes `output/writing-heatmap.json` with the following shape:

```json
{
  "data": {
    "2025-03-12": {
      "count": 2,
      "articles": [
        { "title": "Article title", "url": "/posts/article-slug.html" }
      ]
    }
  },
  "total": 260,
  "streak": 5,
  "most_active_day": "2025-07-04"
}
```

You can consume this file independently of the widget if you want to build your own visualization.

## Requirements

- Python 3.10+
- Pelican 4.5+

## License

MIT
