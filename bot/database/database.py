from config import SQLALCHEMY_URL

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bot.database.models import Base

# создание движка + отключение логов sql
engine = create_async_engine(SQLALCHEMY_URL, echo=False)

async_session = async_sessionmaker(engine)


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)