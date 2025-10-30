"""Base HTTP client for data API."""
import httpx
from src.core.config import settings


class DataAPIClient:
    """Base HTTP client for communication with data_postgres_api."""

    def __init__(self):
        self.base_url = settings.data_api_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0, follow_redirects=True)

    async def get(self, path: str, **kwargs):
        """Make GET request."""
        response = await self.client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, **kwargs):
        """Make POST request."""
        response = await self.client.post(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def delete(self, path: str, **kwargs):
        """Make DELETE request."""
        response = await self.client.delete(path, **kwargs)
        response.raise_for_status()
        return response.status_code

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
