# Changelog

All notable changes to ScholarNova are recorded here. The project follows semantic versioning.

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

### Security

- Desktop packages contain no maintainer API keys, gated datasets, or local databases.
