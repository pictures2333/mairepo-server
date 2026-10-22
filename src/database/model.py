from typing import List, Optional
from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.types import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# Database Base

class Base(DeclarativeBase):
    pass


# Tables

class Chart(Base):
    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, unique=True, nullable=False, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    files: Mapped[List["File"]] = relationship(
        back_populates="chart",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, unique=True, nullable=False, autoincrement=True)

    chart: Mapped["Chart"] = relationship(back_populates="files")
    chart_id: Mapped[int] = mapped_column(ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)

    filename: Mapped[str] = mapped_column(String, nullable=False)
    blobs: Mapped[List["Blob"]] = relationship(
        back_populates="file",
        passive_deletes=True,
    )


class Blob(Base):
    __tablename__ = "blobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, unique=True, nullable=False, autoincrement=True)

    file: Mapped[Optional["File"]] = relationship(back_populates="blobs")
    file_id: Mapped[Optional[int]] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)

    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
