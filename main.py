import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from src.database.database import init_db, close_db
from src.utils.drive import close_drive, init_drive
from src.core.scheduler import run_sync_scheduler
from src.router import blob_router, chart_router
from src import schema

# Lifespan

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    try:
        await init_db()
        try:
            await init_drive()

            sync_scheduler_task = asyncio.create_task(
                run_sync_scheduler(),
                name="mairepo-sync-scheduler"
            )
            try:
                yield
            finally:
                sync_scheduler_task.cancel()
                with suppress(asyncio.CancelledError):
                    await sync_scheduler_task
        finally:
            await close_drive()
    finally:
        await close_db()


# App

app = FastAPI(lifespan=lifespan)

# Routers

app.include_router(chart_router)
app.include_router(blob_router)

# Routes

@app.get("/")
async def index() -> schema.Message:
    return schema.Message(message="Shirakami Fubuki is the cutest fox!")
