from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .api import auth, teams, predict, recommendations, data, matches
from .tasks.scheduler import start_scheduler

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # 缓存预检请求 24 小时，避免重复 OPTIONS
)

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
    """代理外部图片，解决 Flutter Web CORS 跨域问题。"""
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
            "Cache-Control": "public, max-age=86400",  # 缓存 1 天
            "Access-Control-Allow-Origin": "*",
        },
    )