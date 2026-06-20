"""FastAPI-обёртка.

  uvicorn api.main:app
  GET /scan?url=example.ru
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rucompliance.scanner import scan

app = FastAPI(title="RU Compliance Scanner", version="1.0")

# CORS — чтобы лендинг (другой домен) мог дёргать /scan из браузера.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # на проде сузить до своего домена лендинга
    allow_methods=["*"],
    allow_headers=["*"],
)

# поток покупки документов через Робокассу
from api.pay import router as pay_router  # noqa: E402
app.include_router(pay_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/scan")
def scan_endpoint(url: str):
    return scan(url)


@app.get("/cookie-banner")
def cookie_banner_endpoint(policy: str = "/privacy", accent: str = "#0077FF"):
    from fastapi.responses import PlainTextResponse
    from rucompliance.cookiegen import cookie_banner
    return PlainTextResponse(cookie_banner(policy_url=policy, accent=accent))


@app.get("/badge")
def badge_endpoint(url: str):
    from fastapi.responses import Response
    from rucompliance.badge import badge_for
    svg = badge_for(scan(url, crawl=False))   # быстро, одна страница
    return Response(svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "max-age=3600"})
