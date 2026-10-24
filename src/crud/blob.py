from typing import List, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from src.database import model
from src.settings import settings


UNSET = object()


async def read_blobs(
    session:AsyncSession,
    id:object=UNSET,
    limit_to_gc_keep:Literal[True, False, None]=None
) -> List[model.Blob]:
    """
    Read blobs with their files eagerly loaded.

    Args:
        session: Database session used for the query.
        id: Blob ID to query. Use None to query orphan blobs, or leave it unset
            to query all blobs.
        limit_to_gc_keep: True selects blobs within GC_KEEP, False selects
            blobs outside GC_MAX_KEEP, and None disables retention filtering.
            Both retention filters exclude orphan blobs.

    Returns:
        List[model.Blob]: Matching blobs.

    Raises:
        TypeError: If id or limit_to_gc_keep has an unsupported value.
        ValueError: If retention filtering is used when querying orphan blobs.
    """
    if id is not UNSET and id is not None and (
        not isinstance(id, int) or isinstance(id, bool)
    ):
        raise TypeError("id must be an int, None, or UNSET.")
    if (
        limit_to_gc_keep is not True
        and limit_to_gc_keep is not False
        and limit_to_gc_keep is not None
    ):
        raise TypeError("limit_to_gc_keep must be True, False, or None.")
    if id is None and limit_to_gc_keep is not None:
        raise ValueError(
            "limit_to_gc_keep must be None when querying orphan blobs."
        )

    stmt = (
        select(model.Blob)
        .options(joinedload(model.Blob.file))
    )

    if id is None:
        stmt = stmt.where(model.Blob.file_id.is_(None))
    elif id is not UNSET:
        stmt = stmt.where(model.Blob.id == id)

    if limit_to_gc_keep is not None:
        candidate_blob = aliased(model.Blob)
        kept_blob_ids = (
            select(candidate_blob.id)
            .where(candidate_blob.file_id == model.Blob.file_id)
            .order_by(
                candidate_blob.created_at.desc(),
                candidate_blob.id.desc()
            )
            .limit(
                settings.GC_KEEP
                if limit_to_gc_keep
                else settings.GC_MAX_KEEP
            )
            .correlate(model.Blob)
        )
        stmt = stmt.where(model.Blob.file_id.is_not(None))
        if limit_to_gc_keep:
            stmt = stmt.where(model.Blob.id.in_(kept_blob_ids))
        else:
            stmt = stmt.where(model.Blob.id.not_in(kept_blob_ids))

    return list(await session.scalars(stmt))
