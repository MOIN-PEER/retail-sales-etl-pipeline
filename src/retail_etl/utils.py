"""Small shared helpers: retry decorator and timing context manager."""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from typing import Callable, Iterator, Tuple, Type, TypeVar

T = TypeVar("T")
logger = logging.getLogger("retail_etl.utils")


def retry(
    attempts: int = 3,
    backoff_seconds: float = 1.0,
    exceptions: Tuple[Type[BaseException], ...] = (OSError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a function on transient errors with exponential backoff (1s, 2s, 4s...)."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        logger.error("%s failed after %d attempts: %s", func.__name__, attempts, exc)
                        raise
                    wait = backoff_seconds * 2 ** (attempt - 1)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s - retrying in %.1fs",
                        func.__name__, attempt, attempts, exc, wait,
                    )
                    time.sleep(wait)
            raise RuntimeError("unreachable")  # pragma: no cover

        return wrapper

    return decorator


@contextmanager
def timed(step: str, log: logging.Logger) -> Iterator[None]:
    start = time.perf_counter()
    log.info("START  %s", step)
    try:
        yield
    finally:
        log.info("FINISH %s (%.2fs)", step, time.perf_counter() - start)
