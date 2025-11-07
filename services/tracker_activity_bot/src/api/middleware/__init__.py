"""Middleware package for bot request processing."""

from .service_injection import ServiceInjectionMiddleware

__all__ = ["ServiceInjectionMiddleware"]
