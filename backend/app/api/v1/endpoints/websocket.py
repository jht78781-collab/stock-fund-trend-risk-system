import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.exceptions import DataSourceError, StockNotFoundError
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/stocks/{symbol}")
async def stock_quote_stream(websocket: WebSocket, symbol: str) -> None:
    await websocket.accept()
    service = MarketService()

    try:
        while True:
            try:
                payload = await run_in_threadpool(service.get_realtime_quote, symbol)
                await websocket.send_json(
                    {
                        "type": "quote",
                        "data": payload,
                        "risk_notice": settings.RISK_NOTICE,
                    }
                )
            except StockNotFoundError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                await websocket.close(code=1008)
                return
            except DataSourceError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})

            await asyncio.sleep(settings.WS_PUSH_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", symbol)

