"""Scheduler protocol for Dependency Inversion Principle (DIP) compliance."""

from typing import Protocol, Callable, runtime_checkable


@runtime_checkable
class PollSchedulerProtocol(Protocol):
    """
    Protocol for poll scheduling operations.

    Defines the interface for scheduling automatic polls,
    allowing for different implementations and easier testing.

    This protocol enables Dependency Inversion Principle:
    - High-level handlers depend on this abstraction
    - Low-level SchedulerService implements this abstraction
    - No direct dependency on concrete implementation

    Example:
        >>> # Inject via ServiceContainer
        >>> @router.callback_query(F.data == "action")
        >>> async def handler(callback: types.CallbackQuery, services: ServiceContainer):
        >>>     await services.scheduler.schedule_poll(...)
    """

    async def schedule_poll(
        self,
        user_id: int,
        settings: dict,
        user_timezone: str,
        send_poll_callback: Callable,
        bot
    ) -> None:
        """
        Schedule next poll for user based on settings.

        Calculates next poll time considering:
        - Poll interval (weekday vs weekend)
        - Quiet hours configuration
        - User timezone

        Args:
            user_id: Telegram user ID
            settings: User settings dict with poll configuration
            user_timezone: User timezone string (e.g., "Europe/Moscow")
            send_poll_callback: Async function to call when poll is due
            bot: Bot instance to pass to callback

        Example:
            >>> await scheduler.schedule_poll(
            >>>     user_id=12345,
            >>>     settings={"poll_interval_weekday": 120},
            >>>     user_timezone="Europe/Moscow",
            >>>     send_poll_callback=send_automatic_poll,
            >>>     bot=bot
            >>> )
        """
        ...

    async def cancel_poll(self, user_id: int) -> None:
        """
        Cancel scheduled poll for user.

        Args:
            user_id: Telegram user ID

        Example:
            >>> await scheduler.cancel_poll(12345)
        """
        ...

    def start(self) -> None:
        """
        Start the scheduler.

        Must be called before scheduling any jobs.

        Example:
            >>> scheduler.start()
        """
        ...

    def stop(self, wait: bool = True) -> None:
        """
        Stop the scheduler.

        Args:
            wait: If True, wait for pending jobs to complete

        Example:
            >>> scheduler.stop(wait=True)
        """
        ...

    @property
    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        Returns:
            True if scheduler is active

        Example:
            >>> if scheduler.is_running:
            >>>     print("Scheduler is active")
        """
        ...
