from typing import List, Optional, Dict

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, contains_eager, joinedload

from src.database import model
from src.settings import settings


async def read_charts(
    session:AsyncSession,
    do_joined_load:bool=False,
    limit_to_gc_keep:Optional[bool]=None,
    id:Optional[int]=None,
    name:Optional[str]=None
) -> List[model.Chart]:
    """
    Read charts with optional eager loading of files and blobs.

    Args:
        session: Database session used for the query.
        do_joined_load: Whether to eagerly load files and blobs.
        limit_to_gc_keep: When True, load only the latest GC_KEEP blobs for each
            file. When False, load all blobs. Must be a bool when eager loading
            is enabled.
        id: Optional chart ID filter.
        name: Optional chart name filter.

    Returns:
        List[model.Chart]: Matching charts.

    Raises:
        TypeError: If limit_to_gc_keep is not a bool when eager loading is enabled.
    """
    stmt = select(model.Chart)

    if id is not None:
        stmt = stmt.where(model.Chart.id == id)

    if name is not None:
        stmt = stmt.where(model.Chart.name == name)

    if do_joined_load:
        if not isinstance(limit_to_gc_keep, bool):
            raise TypeError(
                "limit_to_gc_keep must be a bool when do_joined_load is enabled."
            )

        if limit_to_gc_keep:
            ranked_blobs = (
                select(
                    model.Blob,
                    func.row_number().over(
                        partition_by=model.Blob.file_id,
                        order_by=(
                            model.Blob.created_at.desc(),
                            model.Blob.id.desc()
                        )
                    ).label("blob_rank")
                )
                .subquery()
            )
            recent_blob = aliased(model.Blob, ranked_blobs)

            stmt = (
                stmt
                .outerjoin(model.Chart.files)
                .outerjoin(
                    recent_blob,
                    and_(
                        recent_blob.file_id == model.File.id,
                        ranked_blobs.c.blob_rank <= settings.GC_KEEP
                    )
                )
                .options(
                    contains_eager(model.Chart.files)
                    .contains_eager(model.File.blobs.of_type(recent_blob))
                )
                .order_by(
                    model.Chart.id,
                    model.File.id,
                    recent_blob.created_at.desc(),
                    recent_blob.id.desc()
                )
            )
        else:
            stmt = stmt.options(
                joinedload(model.Chart.files)
                .joinedload(model.File.blobs)
            )

        stmt = stmt.execution_options(populate_existing=True)
        result = await session.execute(stmt)
        return list(result.unique().scalars())

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
