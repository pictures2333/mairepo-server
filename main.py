from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database.database import init_db, close_db
from src.utils.drive import close_drive, init_drive

# Lifespan

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    await init_db()
    try:
        await init_drive()
        try:
            yield
        finally:
            # shutdown
            await close_drive()
    finally:
        await close_db()


# App

app = FastAPI(lifespan=lifespan)

# Routers

#app.include_router(auth_router)

# Routes

@app.get("/")
async def index() -> dict[str, str]:
    return {"message": "Shirakami Fubuki is the cutest fox!"}
