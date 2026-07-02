# Contributing to ScholarNova

## Development setup

1. Fork and clone the repository.
2. Copy `backend/.env.example` to `backend/.env`.
3. Add only your own development credentials. Never commit them.
4. Install the backend with `pip install -e .` in `backend`.
5. Install the frontend with `npm ci` in `frontend`.

## Before opening a pull request

```bash
cd backend
pytest

cd ../frontend
npm test
npm run build
```

Keep changes focused. Include tests for behavior changes and screenshots for visible UI changes. Do not commit generated databases, model configuration, gated datasets, benchmark logs, or provider credentials.

## Reporting issues

Provide the operating system, deployment method, failing action, expected result, sanitized logs, and reproduction steps. Remove tokens, e-mail addresses, private paper content, and local paths before posting.
