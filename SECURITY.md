# Security policy

## Reporting a vulnerability

Do not publish exploitable security details or credentials in a public issue. Contact the repository owner through the private contact method available on the GitHub profile and include a minimal reproduction.

## Credential handling

- Store provider keys only in ignored `.env` or local configuration files.
- Use separate development, competition, and production credentials.
- Revoke and replace a credential immediately if it appears in chat, a screenshot, a log, an issue, or Git history.
- Do not place licensed benchmark data or private papers in the public repository.

## Deployment

- Replace the default database password and application secret.
- Put the API behind TLS and an authenticated reverse proxy for internet-facing deployments.
- Restrict CORS to the actual frontend origin.
- Back up the database and uploads directory.
- Review dependency alerts and apply security updates.

Supported security updates target the latest `main` branch.
