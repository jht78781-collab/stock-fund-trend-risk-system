from fastapi import APIRouter

from app.api.v1.endpoints import stock, websocket

api_router = APIRouter()
api_router.include_router(stock.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])

