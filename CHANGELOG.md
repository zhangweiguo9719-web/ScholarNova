# Changelog

All notable changes to ScholarNova are recorded here. The project follows semantic versioning.

## [1.1.1] - 2026-07-19

### Added

- Persistent local PDF import for papers whose publisher blocks automated retrieval.
- Explicit full-text/abstract coverage, retrieval-source, failure-detail, and visual-page fields in analysis results.
- Drag and keyboard resizing for the paper detail panel, with locally remembered width.
- OpenAlex, Semantic Scholar, and Crossref DOI resolvers in the legal OA acquisition chain.

### Changed

- PDF downloads are streamed with a 50 MB ceiling, no longer depend on often-blocked HEAD requests, and avoid retrying the same failed URL through multiple metadata providers.
- Importing a PDF clears the previous abstract-only cache and immediately starts a new analysis.
- Unpaywall is skipped unless a valid contact email is configured, avoiding misleading 422 errors.
- Task-specific model rows now inherit the saved default credentials after restart when they use the same provider; credentials never leak across different providers.
- The UI distinguishes a parsed PDF from a model-completed full-text analysis when the provider is temporarily unavailable.
- PDF figure pages use the task-specific vision model when configured; if that provider rejects image input, analysis retries with the full parsed text and reports zero visual pages instead of claiming the images were read.
- Full-text analysis now returns and displays provider-reported prompt, completion, and total Token usage instead of leaving model cost invisible.

### Verified

- 244 non-integration backend tests and 16 frontend tests pass; production frontend build succeeds.
- Multipart PDF upload, persistent status lookup, structured full-text parsing, invalid-file rejection, and DOI resolver fallback are covered by automated tests.
- The reported Science China DOI was tested live: every resolver points to the publisher endpoint, which returns HTTP 418 to automated clients, so ScholarNova now reports the restriction and offers authorized local PDF import.

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
