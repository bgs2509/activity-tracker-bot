"""
HTTP client middleware package for Open/Closed Principle compliance.

This package provides extensible middleware components for HTTP clients,
allowing new functionality to be added without modifying existing code.

Middleware Types:
- Request middleware: Process outgoing requests (logging, auth, headers)
- Response middleware: Process incoming responses (logging, caching, metrics)
- Error middleware: Handle errors and exceptions (retry, fallback, logging)

Usage:
    from src.infrastructure.http_clients.middleware import (
        LoggingMiddleware,
        TimingMiddleware,
        ErrorHandlingMiddleware
    )

    client = DataAPIClient(
        middlewares=[
            LoggingMiddleware(),
            TimingMiddleware(),
            ErrorHandlingMiddleware()
        ]
    )
"""

from .protocols import RequestMiddleware, ResponseMiddleware, ErrorMiddleware
from .logging_middleware import LoggingMiddleware
from .timing_middleware import TimingMiddleware
from .error_middleware import ErrorHandlingMiddleware

__all__ = [
    # Protocols
    "RequestMiddleware",
    "ResponseMiddleware",
    "ErrorMiddleware",
    # Implementations
    "LoggingMiddleware",
    "TimingMiddleware",
    "ErrorHandlingMiddleware",
]
