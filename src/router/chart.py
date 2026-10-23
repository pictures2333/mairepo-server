from typing import List, Optional
import pathlib

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, HTTPException

from src.core import security
from src.core import log
from src.database import database
from src import schema
from src import crud

# logger

logger = log.get_logger("mairepo.router.chart")

# Router

router = APIRouter(prefix="/chart", tags=["chart"])

# Routes

@router.get("/")
@router.get("/{chart_id}")
async def index(
    session:AsyncSession = Depends(database.get_session),
    _:bool = Depends(security.verify_security_token),
    chart_id:Optional[int]=None
) -> List[schema.Chart]:
    db_charts = await crud.read_charts(
        session,
        do_joined_load=True,
        limit_to_gc_keep=True,
        id=chart_id
    )

    return [
        schema.Chart(
            id=db_chart.id,
            name=db_chart.name,
            files=[
                schema.File(
                    id=f.id,
                    filename=f.filename,
                    drive_head_revision_id=f.drive_head_revision_id,
                    blobs=[
                        schema.Blob(
                            id=b.id,
                            drive_revision_id=b.drive_revision_id,
                            created_at=b.created_at
                        )
                        for b in f.blobs
                    ]
                )
                for f in db_chart.files
            ]
        )
        for db_chart in db_charts
    ]
