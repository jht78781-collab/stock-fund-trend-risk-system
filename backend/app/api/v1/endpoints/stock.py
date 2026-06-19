from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.stock import (
    KLineItem,
    PredictionRecordOut,
    StockAnalysisOut,
    StockQuoteOut,
    StockSearchItem,
)
from app.services.exceptions import DataSourceError, StockNotFoundError
from app.services.market_service import MarketService

router = APIRouter()


def get_market_service(db: Session = Depends(get_db)) -> MarketService:
    return MarketService(db=db)


@router.get("/search", response_model=list[StockSearchItem], summary="股票代码或名称查询")
def search_stocks(
    keyword: str = Query(..., min_length=1, description="股票代码或名称关键字"),
    limit: int = Query(20, ge=1, le=100),
    service: MarketService = Depends(get_market_service),
) -> list[dict]:
    try:
        return service.search_stocks(keyword=keyword, limit=limit)
    except DataSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{symbol}/quote", response_model=StockQuoteOut, summary="获取股票实时行情")
def get_quote(
    symbol: str,
    service: MarketService = Depends(get_market_service),
) -> dict:
    try:
        return service.get_realtime_quote(symbol)
    except StockNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{symbol}/history", response_model=list[KLineItem], summary="获取历史 K 线和技术指标")
def get_history(
    symbol: str,
    start_date: str | None = Query(None, description="开始日期，格式 YYYY-MM-DD 或 YYYYMMDD"),
    end_date: str | None = Query(None, description="结束日期，格式 YYYY-MM-DD 或 YYYYMMDD"),
    adjust: str = Query("qfq", pattern="^(qfq|hfq|)$", description="复权方式：qfq、hfq 或空"),
    service: MarketService = Depends(get_market_service),
) -> list[dict]:
    try:
        return service.get_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StockNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{symbol}/analysis", response_model=StockAnalysisOut, summary="股票趋势分析和风险评估")
def analyze_stock(
    symbol: str,
    start_date: str | None = Query(None, description="开始日期，默认近 1 年"),
    end_date: str | None = Query(None, description="结束日期，默认今天"),
    adjust: str = Query("qfq", pattern="^(qfq|hfq|)$", description="复权方式：qfq、hfq 或空"),
    service: MarketService = Depends(get_market_service),
) -> dict:
    try:
        return service.analyze_stock(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StockNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/{symbol}/predictions",
    response_model=list[PredictionRecordOut],
    summary="查询历史预测记录",
)
def list_predictions(
    symbol: str,
    limit: int = Query(20, ge=1, le=100),
    service: MarketService = Depends(get_market_service),
) -> list:
    try:
        return service.list_predictions(symbol=symbol, limit=limit)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"MySQL 查询失败：{exc}") from exc
    except StockNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

