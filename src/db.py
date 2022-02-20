import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

from src import Config

Base = declarative_base()


class AsyncDatabaseSession:

    def __init__(self):

        self._engine = None
        self._session_maker = None
        self.Model = Base

    async def init(self):
        if not self._engine or not self._session_maker:
            self._engine = create_async_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False, )
            self._session_maker = sessionmaker(
                self._engine, expire_on_commit=False, class_=AsyncSession
            )

    @property
    def session(self):

        return self._session_maker()

    def _start(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        loop.run_until_complete(self.init())

    async def stop(self):
        await self._engine.dispose()

    def close(self):
        if self._engine:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            loop.create_task(self._engine.dispose())
            self._engine = None
