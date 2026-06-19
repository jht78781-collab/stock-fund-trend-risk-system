from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import HistoricalQuote, PredictionRecord, StockBasicInfo


class StockRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_basic_info(self, data: dict) -> StockBasicInfo:
        stock = self.db.scalar(select(StockBasicInfo).where(StockBasicInfo.symbol == data["symbol"]))
        if stock is None:
            stock = StockBasicInfo(**data)
            self.db.add(stock)
        else:
            for key, value in data.items():
                setattr(stock, key, value)
        self.db.commit()
        self.db.refresh(stock)
        return stock

    def upsert_history(self, rows: list[dict]) -> int:
        changed = 0
        for row in rows:
            quote = self.db.scalar(
                select(HistoricalQuote).where(
                    HistoricalQuote.symbol == row["symbol"],
                    HistoricalQuote.trade_date == row["trade_date"],
                )
            )
            if quote is None:
                self.db.add(HistoricalQuote(**row))
            else:
                for key, value in row.items():
                    setattr(quote, key, value)
            changed += 1
        self.db.commit()
        return changed

    def create_prediction(self, data: dict) -> PredictionRecord:
        record = PredictionRecord(**data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_predictions(self, symbol: str, limit: int = 20) -> list[PredictionRecord]:
        statement = (
            select(PredictionRecord)
            .where(PredictionRecord.symbol == symbol)
            .order_by(PredictionRecord.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

