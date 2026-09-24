"""FastAPI 入口：启动时初始化数据库，挂载路由。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import papers, chat, search

# 前端静态目录（backend/app/main.py -> 项目根/frontend）
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI 论文阅读助手", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(papers.router)
app.include_router(chat.router)
app.include_router(search.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# 前端静态托管（放在最后兜底：/ 返回 index.html；本地 file:// 打开方式不受影响）
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")