from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from src.database import model
from src.settings import settings


async def read_blob(
    session:AsyncSession,
    blob_id:int,
    limit_to_gc_keep:bool=False
) -> Optional[model.Blob]:
    """
    Read a blob by ID with its file eagerly loaded.

    Args:
        session: Database session used for the query.
        blob_id: Blob ID to query.
        limit_to_gc_keep: Whether the blob must be attached to a file and
            among that file's latest GC_KEEP versions. Enabling this causes
            orphan blobs to be treated as not found because their retention
            rank cannot be verified.

    Returns:
        Optional[model.Blob]: The matching blob, or None when it does not exist
            or, while the limit is enabled, is orphaned or outside GC_KEEP.
    """
    stmt = (
        select(model.Blob)
        .where(model.Blob.id == blob_id)
        .options(joinedload(model.Blob.file))
    )

    if limit_to_gc_keep:
        candidate_blob = aliased(model.Blob)
        recent_blob_ids = (
            select(candidate_blob.id)
            .where(candidate_blob.file_id == model.Blob.file_id)
            .order_by(
                candidate_blob.created_at.desc(),
                candidate_blob.id.desc()
            )
            .limit(settings.GC_KEEP)
            .correlate(model.Blob)
        )
        stmt = stmt.where(
            model.Blob.file_id.is_not(None),
            model.Blob.id.in_(recent_blob_ids)
        )

    return await session.scalar(stmt)
