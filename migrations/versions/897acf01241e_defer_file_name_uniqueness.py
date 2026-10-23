"""defer file name uniqueness

Revision ID: 897acf01241e
Revises: 844e1ec910d8
Create Date: 2026-10-23

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "897acf01241e"
down_revision: Union[str, Sequence[str], None] = "844e1ec910d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "uq_files_chart_id_filename",
        "files",
        type_="unique"
    )
    op.create_unique_constraint(
        "uq_files_chart_id_filename",
        "files",
        ["chart_id", "filename"],
        deferrable=True,
        initially="DEFERRED"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_files_chart_id_filename",
        "files",
        type_="unique"
    )
    op.create_unique_constraint(
        "uq_files_chart_id_filename",
        "files",
        ["chart_id", "filename"]
    )
