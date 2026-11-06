# Changelog

All notable changes to the profile page generator. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [4.0.0] — 2026-11-07

Complete redesign — the old dark-gradient card wall (typing banner, snake,
isocalendar, achievements, stats panels) is gone.

### Changed
- New visual language: hairline editorial style, one indigo accent, every SVG
  adapts to GitHub light/dark via `prefers-color-scheme`, no backgrounds, no
  glow, no animation.
- README structure is visitor-first: Now → Featured work (4 cards) → Open
  source record → Writing → Toolbox. The compiler documentation moved into a
  collapsed `About this page` footnote.
- The generator collapsed from a 30-module `kit/` package into a single
  `build.py`; `accounts.py` is gone, copy lives in `build.COPY`.

### Removed
- typing / snake / isocalendar / people / achievements / stats assets and
  their renderers
- `ARCHITECTURE.md`, `AUDIT_REPORT.md`, `DEVELOPMENT.md`, `SECURITY.md`,
  `CONTRIBUTING.md`, `requirements-optional.txt`
- preview / pack / bench / links targets and scripts

### Kept
- `make gen` / `make verify` / `make test` / `make release` entry points and
  the offline CI contract (generated tree must be byte-reproducible)
- the GitCode / Gitee mirror workflow and its per-platform README isolation
- `scripts/refresh_sections.py` as the only network component (stats snapshot)

## [3.0.0] and earlier

History of the previous generator was dropped in the 4.0.0 rewrite; see git
tags for the old tree.
