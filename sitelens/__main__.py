import os

import uvicorn

from .app import create_app

uvicorn.run(
    create_app(),
    host=os.environ.get("SITELENS_HOST") or "127.0.0.1",
    port=int(os.environ.get("SITELENS_PORT") or 8788),
    proxy_headers=True,
    log_level="info",
)
