from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

from .db import init_db
from .routes_admin import router as admin_router
from .routes_public import router as public_router

NOT_BUILT = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<title>SiteLens</title></head><body style="font-family:sans-serif;padding:40px">
<p>监控台界面还没有构建：在 <code>web/</code> 里运行 <code>npm ci &amp;&amp; npm run build</code>。</p></body></html>"""


def web_dist() -> Path:
    configured = os.environ.get("SITELENS_WEB_DIST")
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[1] / "web" / "dist"


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="SiteLens", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,
    )
    dist = web_dist()

    @app.middleware("http")
    async def private_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/admin"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse({"error": detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        fields = sorted({str(item.get("loc", ["", "?"])[-1]) for item in exc.errors()})
        return JSONResponse({"error": f"参数不正确：{'、'.join(fields)}"}, status_code=422)

    app.include_router(public_router)
    app.include_router(admin_router)

    @app.get("/", response_class=HTMLResponse)
    def index():
        index_file = dist / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return HTMLResponse(NOT_BUILT)

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")
        target = dist / path
        if target.is_file():
            return FileResponse(target)
        index_file = dist / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return HTMLResponse(NOT_BUILT, status_code=200)

    return app
