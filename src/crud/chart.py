from typing import List, Optional, Dict

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import model


async def read_charts(
    session:AsyncSession,
    id:Optional[int]=None,
    name:Optional[str]=None
) -> List[model.Chart]:
    stmt = select(model.Chart)

    if id is not None:
        stmt = stmt.where(model.Chart.id == id)

    if name is not None:
        stmt = stmt.where(model.Chart.name == name)

    return list(await session.scalars(stmt))


async def create_chart(
    session:AsyncSession,
    chart_name:str,
    files:List[Dict[str, str]]
) -> model.Chart:
    """
    Create chart, files and blobs.

    Format of `files`:
    ```
    [
        {
            "filename": "...",
            "filepath": "...",
            "drive_file_id": "...",
            "drive_head_revision_id": "...",
        },
        ...
    ]
    ```
    """
    db_files = []
    for f in files:
        file = model.File(
            filename=f["filename"],
            drive_file_id=f["drive_file_id"],
            drive_head_revision_id=f["drive_head_revision_id"]
        )
        file.blobs.append(
            model.Blob(path=f["filepath"], drive_revision_id=f["drive_head_revision_id"])
        )
        db_files.append(file)
    
    chart = model.Chart(
        name=chart_name,
        files=db_files
    )
    session.add(chart)
    await session.flush()
    await session.refresh(chart)

    return chart


async def delete_chart(
    session:AsyncSession,
    id:Optional[int]=None,
    name:Optional[str]=None
) -> None:
    """
    Delete a chart by ID or name, preferring the ID when both are provided.

    Raises:
        ValueError: If neither ID nor name is provided.
    """
    stmt = delete(model.Chart)

    if id is not None:
        stmt = stmt.where(model.Chart.id == id)
    elif name is not None:
        stmt = stmt.where(model.Chart.name == name)
    else:
        raise ValueError("Either id or name must be provided to delete a chart.")

    await session.execute(stmt)
    return None
