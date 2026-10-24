from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from src.database import model
from src.settings import settings


async def read_blobs(
    session:AsyncSession,
    id:Optional[int]=None,
    limit_to_gc_keep:bool=False
) -> List[model.Blob]:
    """
    Read blobs with their files eagerly loaded.

    Args:
        session: Database session used for the query.
        id: Optional blob ID filter. When omitted, return all matching blobs.
        limit_to_gc_keep: Whether the blob must be attached to a file and
            among that file's latest GC_KEEP versions. Enabling this causes
            orphan blobs to be treated as not found because their retention
            rank cannot be verified.

    Returns:
        List[model.Blob]: Matching blobs. When the limit is enabled, orphaned
            blobs and blobs outside GC_KEEP are excluded.
    """
    stmt = (
        select(model.Blob)
        .options(joinedload(model.Blob.file))
    )

    if id is not None:
        stmt = stmt.where(model.Blob.id == id)

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

    return list(await session.scalars(stmt))
