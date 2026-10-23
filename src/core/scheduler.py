import asyncio

from src.settings import settings
from src.utils.sync import sync


# Lock

scheduler_lock = asyncio.Lock()


# Scheduler

async def run_sync_scheduler() -> None:
    """
    Run sync periodically without overlapping maintenance jobs.
    """
    while True:
        async with scheduler_lock:
            try:
                await sync()
            except Exception:
                # sync() already logs its failure.
                pass

        await asyncio.sleep(settings.RUN_SYNC_INTERVAL)
