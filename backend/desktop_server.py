"""Desktop entry point for the packaged ScholarNova backend."""

import os

import uvicorn


def main() -> None:
    """Run the FastAPI server with desktop-safe defaults."""
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
