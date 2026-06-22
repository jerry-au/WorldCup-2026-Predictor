import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .api import auth, teams, predict, recommendations, data, matches
from .tasks.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# 图片代理可信域名白名单（后缀匹配）
_IMAGE_PROXY_ALLOWED_DOMAINS = [
    "dongqiudi.com",
    "cdn.dongqiudi.com",
    "static.dongqiudi.com",
    "img.dongqiudi.com",
    "sport.guim.co.uk",
    "img.uefa.com",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="World Cup 2026 Predictor",
    description="Match prediction and betting recommendation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # 缓存预检请求 24 小时，避免重复 OPTIONS
)

# ── 全局异常处理器 ──────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s %s — %s", request.method, request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 5000, "message": "Internal server error"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # 将 HTTPException 统一为 {"code": status, "message": detail} 格式
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail)},
    )


# ── 请求日志中间件 ──────────────────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(
        "%s %s → %s (%.3fs)",
        request.method, request.url.path, response.status_code, elapsed,
    )
    return response


app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(predict.router)
app.include_router(recommendations.router)
app.include_router(data.router)
app.include_router(matches.router)

# 静态文件服务（球员头像、国旗等）
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/proxy-image")
async def proxy_image(url: str, request: Request):
    """代理外部图片，解决 Flutter Web CORS 跨域问题。

    仅允许白名单域名，防止 SSRF 攻击。
    """
    hostname = urlparse(url).hostname
    if not hostname or not any(
        hostname == allowed or hostname.endswith("." + allowed)
        for allowed in _IMAGE_PROXY_ALLOWED_DOMAINS
    ):
        raise HTTPException(status_code=403, detail="Domain not allowed")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.dongqiudi.com/",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers, follow_redirects=True)
    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
        },
    )