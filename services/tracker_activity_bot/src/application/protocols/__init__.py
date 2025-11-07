"""
Application protocols for Dependency Inversion Principle (DIP).

This package defines abstract interfaces that high-level modules depend on,
allowing low-level implementations to be injected at runtime.

Benefits:
- Testability: Easy to mock protocols in unit tests
- Flexibility: Swap implementations without changing dependent code
- Decoupling: High-level logic doesn't depend on low-level details

Usage:
    from src.application.protocols import PollSchedulerProtocol

    class MockScheduler(PollSchedulerProtocol):
        async def schedule_poll(self, ...):
            pass  # Mock implementation
"""

from .scheduler import PollSchedulerProtocol

__all__ = ["PollSchedulerProtocol"]
