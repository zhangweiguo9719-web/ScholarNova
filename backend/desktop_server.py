"""Desktop entry point for the packaged ScholarNova backend."""

import os

import uvicorn


def main() -> None:
    """Run the FastAPI server with desktop-safe defaults."""
    # PyInstaller bundles do not always resolve the system CA store. Point
    # every TLS consumer (httpx, requests, ssl) at the CA bundle shipped
    # alongside the package so outbound HTTPS (LLM, OpenAlex, Crossref, ...)
    # works after a fresh install.
    try:
        import certifi

        _ca = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", _ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", _ca)
    except Exception:
        pass

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "18765"))
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
