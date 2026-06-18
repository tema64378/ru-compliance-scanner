"""FastAPI-обёртка.

  uvicorn api.main:app
  GET /scan?url=example.ru
"""

from fastapi import FastAPI

from rucompliance.scanner import scan

app = FastAPI(title="RU Compliance Scanner", version="1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/scan")
def scan_endpoint(url: str):
    return scan(url)
