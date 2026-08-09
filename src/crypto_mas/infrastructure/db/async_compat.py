"""Async compatibility layer for synchronous database operations.

Provides a utility to run synchronous SQLAlchemy calls in a thread pool,
preventing event loop blocking in async contexts.
"""

import asyncio
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


async def run_sync(func: Callable[..., T], *args: object) -> T:
    """Run a synchronous function in a thread pool executor.

    Use this to wrap synchronous database operations (e.g. session.commit())
    inside async functions to avoid blocking the event loop.

    Usage:
        await run_sync(self.db.commit)
        result = await run_sync(self.db.execute, query)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)
