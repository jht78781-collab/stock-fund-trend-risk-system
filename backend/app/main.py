import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as exc:
        logger.warning("Database initialization failed. API will still start: %s", exc)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="第一阶段股票分析 MVP：行情查询、K 线指标、规则预测、风险评估和 WebSocket 推送。",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", summary="服务信息")
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "risk_notice": settings.RISK_NOTICE,
    }


@app.get("/health", summary="健康检查")
def health() -> dict:
    return {"status": "ok"}

