"""Base HTTP client for data API."""
import logging
import time
import httpx
from src.core.config import settings

logger = logging.getLogger(__name__)


class DataAPIClient:
    """Base HTTP client for communication with data_postgres_api."""

    def __init__(self):
        self.base_url = settings.data_api_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0, follow_redirects=True)

    async def get(self, path: str, **kwargs):
        """Make GET request."""
        logger.debug(
            f"HTTP GET request",
            extra={
                "method": "GET",
                "path": path,
                "base_url": self.base_url,
                "params": kwargs.get("params")
            }
        )
        start_time = time.time()
        try:
            response = await self.client.get(path, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"HTTP GET response",
                extra={
                    "method": "GET",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "response_size": len(response.content) if response.content else 0
                }
            )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"HTTP GET failed",
                extra={
                    "method": "GET",
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

    async def post(self, path: str, **kwargs):
        """Make POST request."""
        logger.debug(
            f"HTTP POST request",
            extra={
                "method": "POST",
                "path": path,
                "base_url": self.base_url,
                "has_json": "json" in kwargs,
                "has_data": "data" in kwargs
            }
        )
        start_time = time.time()
        try:
            response = await self.client.post(path, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"HTTP POST response",
                extra={
                    "method": "POST",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "response_size": len(response.content) if response.content else 0
                }
            )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"HTTP POST failed",
                extra={
                    "method": "POST",
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

    async def patch(self, path: str, **kwargs):
        """Make PATCH request."""
        logger.debug(
            f"HTTP PATCH request",
            extra={
                "method": "PATCH",
                "path": path,
                "base_url": self.base_url,
                "has_json": "json" in kwargs,
                "has_data": "data" in kwargs
            }
        )
        start_time = time.time()
        try:
            response = await self.client.patch(path, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"HTTP PATCH response",
                extra={
                    "method": "PATCH",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "response_size": len(response.content) if response.content else 0
                }
            )

            response.raise_for_status()
            return response.json()
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"HTTP PATCH failed",
                extra={
                    "method": "PATCH",
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

    async def delete(self, path: str, **kwargs):
        """Make DELETE request."""
        logger.debug(
            f"HTTP DELETE request",
            extra={
                "method": "DELETE",
                "path": path,
                "base_url": self.base_url,
                "params": kwargs.get("params")
            }
        )
        start_time = time.time()
        try:
            response = await self.client.delete(path, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"HTTP DELETE response",
                extra={
                    "method": "DELETE",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2)
                }
            )

            response.raise_for_status()
            return response.status_code
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"HTTP DELETE failed",
                extra={
                    "method": "DELETE",
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
