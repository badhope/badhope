# Changelog

All notable changes to the profile page generator. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Removed
- Obsolete contribution-snake workflow and its `output` branch payload; the
  page has not used it since the celestial rebuild.
- Legacy GitCode/Gitee CI copies that referenced deleted scripts, plus old
  card/icon data left in the mirrors.

### Fixed
- Gitee featured grid now points at the existing `CodePocket` repo instead of a
  missing `shopcash` path; the CSDN channel says archive/manual rather than
  claiming a scheduler that is not installed.

### Changed
- Stats refresh now counts personal, non-fork repositories on GitHub, Gitee
  and GitCode; the weekly job is no longer allowed to fail silently.
- Rebuilt the shared profile template around a celestial theme: star fields,
  constellation lines, a gold-rimmed rotating starchart (SMIL, 180s), and
  light/dark palettes that read as a day-sky atlas rather than a plain white
  page. One source still renders all five profiles.

## [4.1.0] — 2026-11-07

### Added
- Rotating taiji centerpiece (SMIL, self-drawn, adaptive light/dark)
- Animated typing strip — rotating phrases, self-hosted, no external service
- Contribution snake via Platane/snk (light + dark variants, published to the `output` branch)
- Stats trio: github-readme-stats, streak-stats, top-langs with picture-pair theming
- Language switcher (English / 中文 / 日本語) at the top of every GitHub README

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
