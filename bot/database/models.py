from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str]
    proxy: Mapped[str]


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(primary_key=True)
    subs_count: Mapped[int]
    sub_duration_months: Mapped[int]
    channels_list: Mapped[str]
    finish_date: Mapped[str]
    is_used: Mapped[str]