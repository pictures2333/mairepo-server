from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import model


async def read_files_of_chart(
    session:AsyncSession,
    chart_id:int,
    id:Optional[int]=None,
    drive_file_id:Optional[str]=None
) -> List[model.File]:
    stmt = select(model.File).where(model.File.chart_id == chart_id)

    if id is not None:
        stmt = stmt.where(model.File.id == id)

    if drive_file_id is not None:
        stmt = stmt.where(model.File.drive_file_id == drive_file_id)

    return list(await session.scalars(stmt))


async def create_file(
    session:AsyncSession,
    chart_id:int,
    filename:str,
    blob_path:str,
    drive_file_id:str,
    drive_head_revision_id:str
) -> model.File:
    database_file = model.File(
        chart_id=chart_id,
        filename=filename,
        drive_file_id=drive_file_id,
        drive_head_revision_id=drive_head_revision_id,
        blobs=[
            model.Blob(
                path=blob_path,
                drive_revision_id=drive_head_revision_id
            )
        ]
    )
    session.add(database_file)
    await session.flush()
    await session.refresh(database_file)

    return database_file


async def delete_file(
    session:AsyncSession,
    chart_id:int,
    drive_file_id:str
) -> None:
    stmt = delete(model.File).where(
        model.File.chart_id == chart_id,
        model.File.drive_file_id == drive_file_id
    )
    await session.execute(stmt)

    return None


async def update_file(
    session:AsyncSession,
    chart_id:int,
    drive_file_id:str,
    filename:Optional[str]=None,
    blob_path:Optional[str]=None,
    drive_head_revision_id:Optional[str]=None
) -> None:
    """
    Update a file by chart ID and Drive file ID.

    `filename` may be updated independently. To add a new blob, `blob_path`
    and `drive_head_revision_id` must be provided together.

    Raises:
        ValueError: If the update arguments are invalid or the file does not
            exist.
    """
    has_blob_path = blob_path is not None
    has_revision_id = drive_head_revision_id is not None
    if has_blob_path != has_revision_id:
        raise ValueError(
            "blob_path and drive_head_revision_id must be provided together."
        )
    if filename is None and not has_blob_path:
        raise ValueError("At least one file field must be updated.")

    update_values = {}
    if filename is not None:
        update_values["filename"] = filename
    if drive_head_revision_id is not None:
        update_values["drive_head_revision_id"] = drive_head_revision_id

    stmt = (
        update(model.File)
        .where(
            model.File.chart_id == chart_id,
            model.File.drive_file_id == drive_file_id
        )
        .values(**update_values)
        .returning(model.File.id)
    )
    resolved_file_id = await session.scalar(stmt)
    if resolved_file_id is None:
        raise ValueError("File does not exist.")

    if blob_path is not None and drive_head_revision_id is not None:
        session.add(
            model.Blob(
                file_id=resolved_file_id,
                path=blob_path,
                drive_revision_id=drive_head_revision_id
            )
        )
        await session.flush()

    return None
