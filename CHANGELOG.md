# Changelog

All notable changes to ScholarNova are recorded here. The project follows semantic versioning.

## [1.1.0] - 2026-07-17

### Added

- Live search elapsed time and per-call source/API/query/result/latency status.
- Intentional repeat search for the same query and per-paper temporary analysis retention inside one search run.
- Legal open-access PDF acquisition with structured full-text, table, figure-caption, and optional visual-page analysis.
- Title-to-Chinese translation controls on result cards.
- OpenAlex journal indicators plus authorized CSV/JSON import for JCR, historical CAS, and SJR quartiles.
- Institutional-library query handoff and separate real HTTP(S) campus-proxy configuration.
- Portable-build desktop shortcut self-healing.

### Changed

- Query-planning deadline is bounded at 12 seconds and scholarly sources are reported as each parallel call completes.
- JCR/CAS/SJR quartiles are never inferred; provenance and year are shown for imported records.
- Full-text analysis explicitly reports whether it used full text, visual pages, or abstract-only fallback.

### Verified

- 237 non-integration backend tests and 16 frontend tests pass.
- Live Crossref/OpenAlex search returned 12 ranked results in 16.8 seconds with two traceable API calls.
- An open arXiv PDF produced 47,834 characters of section-aware context and two visual pages.

## [1.0.0] - 2026-07-16

### Added

- Windows installer and portable desktop editions with a dedicated ScholarNova icon.
- Automatic startup of the bundled FastAPI backend and local frontend.
- Per-user local database, generated files, model configuration, and logs under AppData.
- GitHub Actions workflow that publishes Windows executables for version tags.
- Chinese Windows desktop release and troubleshooting guide.

### Fixed

- Packaged runtime paths for generated images and research-route diagrams.
- Relative diagram URLs for desktop and self-hosted deployments.
- Lightweight desktop liveness check and pinned Pydantic build dependency compatibility.
- Search creation now returns its `202 pending` response immediately while retaining the asynchronous worker task.
- Model connection checks have a 15-second deadline, and duplicate nested LLM retries were removed.
- Desktop builds explicitly disable electron-builder auto-publish so the release workflow performs one authenticated publish step.

### Security

- Desktop packages contain no maintainer API keys, gated datasets, or local databases.
