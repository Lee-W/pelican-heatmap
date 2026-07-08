# pelican-heatmap

A [Pelican](https://getpelican.com) plugin that generates a GitHub-style writing activity heatmap for your blog. At build time it scans all your articles and produces a JSON data file; a self-contained JS + CSS widget reads that file and renders an interactive calendar you can drop into any page.

---

## Features

- **GitHub-style heatmap** — one cell per day, four color levels based on post frequency
- **Year navigation** — scroll back through your entire writing history with ‹ › buttons; the view always opens on the most recent year
- **Live stats** — posts in the current view window, all-time total, and current streak
- **Clickable cells** — click or tap any day to pin a tooltip listing that day's articles with links; click again or press Escape to dismiss
- **Dark mode** — respects `prefers-color-scheme` automatically
- **Reduced motion** — respects `prefers-reduced-motion` by disabling animations
- **Responsive** — cell size scales with viewport via `clamp()`; works on mobile and large screens
- **Accessible** — keyboard-navigable year buttons with visible focus ring, `aria-label` for screen readers, Escape to dismiss tooltips, `aria-busy` loading state, `<noscript>` fallback support
- **Touch-friendly** — dedicated touch handling for tooltips on mobile devices
- **i18n** — built-in locales (`en`, `zh-TW`) via `window.HM_LANG`, or full custom override via `window.HM_LOCALE`
- **Customizable** — every element has a named CSS class; colors and sizing controlled by CSS custom properties (`--hm-level-1`–`4`, `--hm-cell-size`, etc.)
- **Configurable data source** — override the JSON URL via `data-src` attribute or `window.HM_DATA_URL`
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

The plugin copies `pelican_heatmap.css` and `pelican_heatmap.js` to `output/static/heatmap/` automatically at build time. Add these three lines wherever you want the heatmap to appear — a dedicated page, your about page, or a sidebar:

```html
<link rel="stylesheet" href="/static/heatmap/pelican_heatmap.css">
<div id="writing-heatmap"></div>
<script src="/static/heatmap/pelican_heatmap.js" defer></script>
```

In a Jinja2 template:

```html
<link rel="stylesheet" href="{{ SITEURL }}/static/heatmap/pelican_heatmap.css">
<div id="writing-heatmap"></div>
<script src="{{ SITEURL }}/static/heatmap/pelican_heatmap.js" defer></script>
```

### 3. Build

```bash
pelican content
```

The plugin generates `output/writing-heatmap.json` and copies the static assets. That's it.

---

## Localization

The widget automatically reads `<html lang="...">` to pick the right locale. For example, if your page has `<html lang="zh-TW">`, the heatmap renders in Taiwanese Mandarin with no extra configuration.

Available built-in locales: `en` (default), `zh-TW`.

You can explicitly override with `window.HM_LANG`:

```html
<script>window.HM_LANG = "zh-TW";</script>
```

Resolution order: `window.HM_LANG` > `<html lang>` > `en`.

You can also override individual keys on top of any locale with `window.HM_LOCALE`:

```html
<script>
window.HM_LOCALE = { no_posts: '無文章' }; // override just one key
</script>
```

All keys are optional — omitted keys fall back to the resolved locale's defaults.

The heatmap data (`writing-heatmap.json`) is shared across all languages — only the UI strings change per locale.

---

## Custom data URL

By default the widget fetches `/writing-heatmap.json`. Override this if your site is served from a subpath:

```html
<div id="writing-heatmap" data-src="/blog/writing-heatmap.json"></div>
```

Or via JavaScript:

```html
<script>window.HM_DATA_URL = "/blog/writing-heatmap.json";</script>
```

Resolution order: `data-src` attribute > `window.HM_DATA_URL` > `/writing-heatmap.json`.

---

## No-JavaScript fallback

Place fallback content inside the mount div. The widget replaces it once JS loads:

```html
<div id="writing-heatmap">
  <noscript>
    <p>Enable JavaScript to see the writing activity heatmap.</p>
  </noscript>
  <p class="hm-loading">Loading heatmap…</p>
</div>
```

---

## Customization

### CSS custom properties

Override these in `:root` or any parent selector:

| Property | Default (light) | Description |
| --- | --- | --- |
| `--hm-cell-size` | `clamp(10px, 1.2vw, 18px)` | Cell and row height; scales the whole grid |
| `--hm-cell-empty` | `#e8e6e1` | Empty cell color |
| `--hm-level-1` | `#b5d8a4` | Level 1 cell color (lowest activity) |
| `--hm-level-2` | `#6db86a` | Level 2 cell color |
| `--hm-level-3` | `#3a9142` | Level 3 cell color |
| `--hm-level-4` | `#1d6230` | Level 4 cell color (highest activity) |
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
#writing-heatmap {
  --hm-level-1: #a8c8f8;
  --hm-level-2: #5a9fd4;
  --hm-level-3: #2376b7;
  --hm-level-4: #0d4f8a;
}
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
.hm-loading                    loading placeholder (replaced by widget)
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
  "most_active_day": "2025-07-04"
}
```

The bundled widget calculates the current day streak and current week streak in the browser from `data`, using the visitor's current date. This keeps those live stats accurate even when your site is static and the JSON file was generated earlier. You can consume this file independently of the widget if you want to build your own visualization.

## Requirements

- Python 3.10+
- Pelican 4.5+

## License

MIT
