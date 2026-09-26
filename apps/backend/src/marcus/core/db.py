from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from marcus.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, isolation_level="REPEATABLE READ")
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    # All HTTP dependencies use function scope: commit must finish before sending a success response.
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
