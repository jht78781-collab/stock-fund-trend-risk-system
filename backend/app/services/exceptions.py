class StockServiceError(Exception):
    """Base exception for stock service failures."""


class StockNotFoundError(StockServiceError):
    """Raised when a stock symbol is not found in the data source."""


class DataSourceError(StockServiceError):
    """Raised when the upstream financial data source fails."""

