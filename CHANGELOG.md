# Changelog

All notable changes to ScholarNova are recorded here. The project follows semantic versioning.

## [Unreleased]

### Added

- Optional hybrid retrieval with an independent embedding profile, local vector cache, cosine ranking, and RRF fusion over BM25 results.
- Embedding connection testing for Ollama, OpenAI, Zhipu, Qwen, and custom OpenAI-compatible endpoints.
- Retrieval-mode and embedding-token observability in research-assistant responses and the UI.
- A four-query bilingual/cross-language retrieval golden set that keeps hybrid Top-1 quality above the BM25 baseline.
- Page-aware PDF sections and figure captions, plus structured section/page/chunk locators for bilingual research-assistant citation cards.
- Versioned `paper_chunks` features for authorized PDF abstracts, sections, tables, and figure captions, indexed into the same local retrieval pipeline as knowledge and Zotero.
- A provider-neutral `RetrievalChunk` contract and dependency-free Chinese/English BM25 retrieval layer for research-assistant evidence.
- The first FTI-style feature pipeline: versioned, content-addressed knowledge chunks with lazy backfill and lifecycle synchronization.
- A ScholarNova-specific FTI architecture map covering collection, feature, evaluation/optimization, inference, observability, and release gates.
- Read-only Zotero Local API detection and collection discovery from the Settings page.
- Explicit import of up to 100 Zotero bibliographic records with DOI-based idempotent updates.
- A zero-network local-library search source so imported Zotero papers participate in normal ScholarNova searches.
- A traceable research-assistant MVP that retrieves evidence from the ScholarNova knowledge base and live local Zotero before invoking the configured model.
- An in-app Zotero setup checklist, detected version display, and a clear Zotero 10+ write-back requirement notice.
- A Chinese client-product roadmap covering model portability, fast/deep search, evidence-grounded RAG, authorized library access, reference-manager adapters, MCP boundaries, rollout phases, and acceptance metrics.

### Security

- Embedding credentials are isolated from chat credentials, stored only by the local backend, and never returned to browser storage.
- Zotero access is pinned to `127.0.0.1:23119`; users cannot supply an arbitrary integration URL.
- The integration never writes to Zotero, never accesses `zotero.sqlite` directly, and does not upload a user's library.

### Changed

- The research assistant now uses BM25 by default, optionally embeds a source-balanced pool of at most 256 candidates, fuses rankings with RRF, and transparently falls back to BM25 on every semantic-service failure.
- Embeddings are cached by provider, model, and normalized input hash so repeated content does not consume additional embedding tokens.
- PDF retrieval features now use `pdf-parser-chunker-v2`; analyzing an older imported PDF deterministically refreshes its locators without changing the original file.
- Search, analysis, and research-assistant requests now use independent local rate-limit buckets, so one workflow cannot consume another workflow's allowance.
- PDF upload and full-text analysis synchronize deterministic retrieval features without making an additional LLM call.
- The research assistant now ranks ScholarNova knowledge, parsed PDF, and live Zotero chunks in one candidate pool, limits each document to two evidence chunks, and performs no extra model call for retrieval.
- The research assistant now retrieves diverse, relevant knowledge chunks instead of truncating whole knowledge records into the model context.
- Refreshed the Zhipu GLM selector with current official model IDs, including GLM-5.2 and lower-cost Flash options.
- Zhipu connection probes now disable hidden reasoning and skip retries, preventing an empty tiny probe or an overloaded model from looking like a broken API key.
- Model-test timeouts now return an actionable message instead of an empty error.

### Fixed

- Routed ScholarNova usage questions to the built-in product guide instead of forcing unrelated paper evidence, and stopped knowledge retrieval from falling back to arbitrary recent items when no relevant match exists.
- Scoped the large landing-page hero styles to the home page so they no longer create excessive whitespace or oversized typography on the research-assistant page.
- Kept an empty assistant conversation at the top of the page instead of automatically scrolling to the composer on first load or after clearing.
- Prevented shared card paragraph styles from overriding the user-message contrast in the research assistant.

### Security

- Model credentials are no longer persisted in browser storage or returned by the configuration API; blank saves preserve matching secrets already stored by the local backend.

### Verified

- 282 non-integration backend tests and 18 frontend tests pass; page-aware parsing, hybrid ranking, vector-cache reuse, token accounting, and BM25 fallback are covered without calling a live model.
- The production frontend build succeeds; the four-case retrieval regression fixture improves Top-1 from BM25 3/4 to hybrid 4/4 and is explicitly not presented as a competition benchmark.
- TypeScript checks are clean. Local transactional validation created four PDF features, retrieved two relevant chunks, and rolled the test record back without invoking a model.
- 13 focused Zotero, local-library, and research-assistant tests pass. The offline backend suite remains green; three live Semantic Scholar checks may receive the provider's HTTP 429 rate limit.
- The three remaining full-suite failures are live Semantic Scholar integration checks returning HTTP 429, not local regressions.
- All 16 frontend tests, TypeScript checks, and the production frontend build pass.

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
