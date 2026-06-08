# Deployment & Operations

This is the README behind [github.com/badhope](https://github.com/badhope).
Everything in this document is hand-written, **no bot runs on its own.**

---

## 📂 File map

```
.
├── README.md               # English (default — GitHub renders this on the profile)
├── README.zh-CN.md         # Chinese mirror
├── DEPLOYMENT.md           # ← you are here
├── assets/
│   ├── taiji.svg           # Slowly rotating Tai Chi (60s / revolution)
│   ├── starry-banner.svg   # Top banner with the Big Dipper (北斗七星)
│   └── starry-band.svg     # Mid / bottom starry dividers
├── scripts/
│   └── generate.py         # Manual refresh: repos, CSDN, daily quote, stats
└── .github/workflows/
    └── validate.yml        # PR-only validator (no auto-run, no auto-merge)
```

---

## ✍️ Hand-edit zones

Anything outside an `<!-- AUTO:KEY:START --> ... <!-- AUTO:KEY:END -->` block is yours.

The currently populated `AUTO` keys:

| Key                | What it produces                                            |
|--------------------|-------------------------------------------------------------|
| `SUMMARY`          | "As of YYYY-MM-DD UTC — N public repos · M total ⭐ …" line  |
| `FEATURED`         | Top 6 repos by ⭐, compact list                              |
| `REPOS_GRID`       | Top 9 repos by ⭐, 3×3 card grid (HTML)                     |
| `REPOS_TAIL`       | Repos ranked 10 and below, flex-wrap pill cloud (reflows on mobile) |
| `LANG_BARS`        | Horizontal bar chart of language share                      |
| `TOPIC_CLOUD`      | Frequency-weighted topic pills                              |
| `CSDN`             | Latest 5 CSDN articles (date + title + link)                |
| `QUOTE`            | One quote per UTC day (author + body)                       |

To add a new auto-populated block: drop a new marker pair into the README, then
add a renderer + key to `scripts/generate.py` (see `main()` near the bottom).

---

## 🔄 Refreshing the auto sections

### Local (recommended — keeps you in control)

```bash
# 1. clone
git clone https://github.com/badhope/badhope.git
cd badhope

# 2. install (stdlib only — no pip packages needed)
#    (you're done with step 2; there is no step 2)

# 3. run
python scripts/generate.py
```

The script will:

1. fetch all public repos from `https://api.github.com/users/badhope/repos`
2. sort them by ⭐ (descending)
3. fetch your CSDN RSS at `https://blog.csdn.net/weixin_56622231/rss/list`
4. fetch a quote from `https://api.quotable.io/random` (falls back to ZenQuotes)
5. write the new content into both `README.md` and `README.zh-CN.md`

Then `git add -A && git commit -m "chore: refresh profile" && git push`.

GitHub's anonymous rate limit is 60 req/hr. If you hit it, wait an hour
or set `GITHUB_TOKEN` in your environment for the script to use
automatically.

### CI (PR-only validation, never auto-merges)

`.github/workflows/validate.yml` runs on:

- every **pull request** opened against `main`
- every **push** to `main**
- the **manual "Run workflow"** button in the Actions tab

It does **not** run on a schedule. It does **not** push. It does **not**
merge. It only checks that:

- all `assets/*.svg` exist and are non-empty
- all `AUTO:*` markers are populated
- `python scripts/generate.py` produces no diff against the committed README
- `scripts/generate.py` is syntactically valid Python

If the README has drifted, CI fails with a clear hint. The maintainer
runs the script locally, commits, pushes, and merges.

### Re-enabling scheduled auto-refresh (optional)

If you later want a daily bot to open a PR, restore a schedule + the
`peter-evans/create-pull-request` step. Sketch:

```yaml
on:
  schedule:
    - cron: "0 0 * * *"   # 00:00 UTC = 08:00 Beijing
  workflow_dispatch:
permissions:
  contents: read
  pull-requests: write
jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python scripts/generate.py
      - uses: peter-evans/create-pull-request@v6
        with:
          branch: profile-bot/auto-refresh
          delete-branch: true
          title: "chore: daily profile refresh"
          add-paths: |
            README.md
            README.zh-CN.md
```

**You still merge the PR yourself** — `create-pull-request` will not
auto-merge even with extra config.

---

## 🎨 Design tokens

| Token            | Value                                       |
|------------------|---------------------------------------------|
| Bg deep          | `#0f0e2e`                                   |
| Bg mid           | `#1e1b4b`                                   |
| Bg high          | `#312e81`                                   |
| Accent violet    | `#a78bfa`                                   |
| Accent indigo    | `#818cf8`                                   |
| Accent cyan      | `#67e8f9`                                   |
| Text light       | `#e6e7ee`                                   |
| Text muted       | `#a5b4fc`                                   |
| Star             | `#ffffff` (with `#c4b5fd` glow)             |
| Typewriter font  | Cormorant Garamond (via readme-typing-svg)  |

To retheme, search-and-replace these hex codes across the SVG assets
and inside the inline `style="…"` blocks emitted by `scripts/generate.py`.

---

## 🛠 Troubleshooting

**GitHub rate-limit hit (`403 rate limit exceeded`)**
Wait an hour, or set a `GITHUB_TOKEN` env var before running the script.

**CSDN feed empty**
CSDN occasionally blocks unauthenticated RSS. The script logs to stderr
and renders an empty-state note; the rest of the README still works.

**Taiji not spinning**
SVG `<style>` CSS animations are sandboxed on some renderers (notably
mobile Twitter cards and RSS readers). The static frame is always visible.

**Typing animation not loading**
`readme-typing-svg.demolab.com` is a free third-party service. If it
stops responding, replace the `https://readme-typing-svg.demolab.com?…`
URL in `README.md` / `README.zh-CN.md` with a self-hosted equivalent,
or remove the `<img>` tag entirely.

**Big Dipper position looks wrong at narrow widths**
The banner uses `preserveAspectRatio="xMidYMid slice"` so it crops on
mobile rather than squishing. If you need a different aspect, edit
`assets/starry-banner.svg`.

---

## 🪪 License

MIT for the code in `scripts/`. SVG assets and the README prose are
yours to do whatever you want with.
