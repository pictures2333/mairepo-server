from typing import Optional, List
from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.types import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# Database Base

class Base(DeclarativeBase):
    pass


# Tables

class Chart(Base):
    __tablename__ = "charts"
    __table_args__ = (
        UniqueConstraint("name", name="uq_charts_name"),
    )

    id:Mapped[int] = mapped_column(Integer, primary_key=True)
    name:Mapped[str] = mapped_column(String, nullable=False)
    files:Mapped[List["File"]] = relationship(
        back_populates="chart",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("chart_id", "filename", name="uq_files_chart_id_filename"),
    )

    id:Mapped[int] = mapped_column(Integer, primary_key=True)

    chart_id:Mapped[int] = mapped_column(ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    chart:Mapped["Chart"] = relationship(back_populates="files")

    filename:Mapped[str] = mapped_column(String, nullable=False)
    drive_file_id:Mapped[str] = mapped_column(String, unique=True, nullable=False)
    drive_head_revision_id:Mapped[str] = mapped_column(String, nullable=False)
    blobs:Mapped[List["Blob"]] = relationship(
        back_populates="file",
        passive_deletes=True
    )


class Blob(Base):
    __tablename__ = "blobs"
    __table_args__ = (
        UniqueConstraint("file_id", "drive_revision_id", name="uq_blobs_file_id_drive_revision_id"),
    )

    id:Mapped[int] = mapped_column(Integer, primary_key=True)

    path:Mapped[str] = mapped_column(String, unique=True, nullable=False)
    drive_revision_id:Mapped[str] = mapped_column(String, nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    file_id:Mapped[Optional[int]] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    file:Mapped[Optional["File"]] = relationship(back_populates="blobs")
