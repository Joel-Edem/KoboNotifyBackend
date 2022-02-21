import asyncio
from asyncio.queues import Queue
from typing import Optional
from aiosmtplib import SMTP, SMTPConnectError
from logger import logger
import ssl
import certifi

# logger = get_logger()
from src.Config import SMTPConfig


class AsyncSMTPConnection:

    def __init__(self, pool):
        self.pool: AsyncSMTPConnectionPool = pool
        self._connection: Optional[SMTP] = None
        self.is_active = False

    async def send_message(self, *args, **kwargs):
        try:
            await self.connect()
            if self._connection:
                return await self._connection.send_message(*args, **kwargs)

        finally:
            self.is_active = False
            await self.close()

    async def connect(self):
        if not self._connection or not self._connection.is_connected:
            self._connection = await self.pool.get_smtp_connection(self)
        if self._connection:
            self.is_active = True

    async def close(self):
        if self._connection:
            slept_for = 0
            while self.is_active and slept_for < 5:
                slept_for += 1
                await asyncio.sleep(0)

            await self.pool.return_to_pool(self._connection, self)
            self.is_active = False
            self._connection = None


class AsyncSMTPConnectionPool:
    LOG_NAME = {"color": 'cyan', "location": "AsyncSMTPConnectionPool"}

    def __init__(self, max_connections: int = 12, loop=None):
        self.max_connections = max_connections
        self.min_connections = int(max_connections / 3) or 1
        self.connections = Queue()
        self.loop = loop or asyncio.get_event_loop()
        self._active_connections = {}
        self._is_stopping = False

    async def start(self):
        self._is_stopping = False
        c = self.min_connections - self.connections.qsize()
        if c > 0:
            logger.debug(f"Creating {c} SMTP connections", self.LOG_NAME)
            for i in range(c):
                self.loop.create_task(self.create_connection())
            logger.debug(f"SMTP CONNECTIONS CREATED", self.LOG_NAME)

    async def _get_free_smtp_connections(self):
        """:return all connections in queue"""
        free_conns = []
        logger.debug("closing smtp conns", self.LOG_NAME)
        while 1:
            try:
                conn: SMTP = self.connections.get_nowait()
                self.connections.task_done()
                free_conns.append(conn)
            except asyncio.QueueEmpty:
                break
        return free_conns

    async def stop(self):
        # close all connections in queue
        self._is_stopping = True
        logger.debug("Getting free connections", self.LOG_NAME)
        free_cons: list[SMTP] = await self._get_free_smtp_connections()
        t = [conn.quit(3) for conn in free_cons if conn.is_connected]
        await asyncio.gather(*t)
        logger.debug("free connections closed", self.LOG_NAME)

        logger.debug("Getting active smtp connections", self.LOG_NAME)
        close_active = [conn.close() for conn in self._active_connections]
        await asyncio.gather(*close_active)
        logger.debug("active conns gathered", self.LOG_NAME)

        logger.debug("closing smtp conns", self.LOG_NAME)
        free_cons: list[SMTP] = await self._get_free_smtp_connections()
        close_conns = [conn.quit() for conn in free_cons if conn.is_connected]
        await asyncio.gather(*close_conns)
        logger.debug("All smtp conns closed", self.LOG_NAME)

    async def get_connection(self) -> Optional[AsyncSMTPConnection]:
        if not self._is_stopping:
            return AsyncSMTPConnection(self)

    async def get_smtp_connection(self, obj: Optional[AsyncSMTPConnection] = None) -> SMTP:
        # if no connections exist check if we can create more
        if self.connections.empty() and (self.connections.qsize() < self.max_connections):
            self.loop.create_task(self.create_connection())
        conn: SMTP = await self.connections.get()
        while not conn.is_connected:
            # create task to reconnect
            self.loop.create_task(self.reconnect(conn))
            conn = await self.connections.get()
        if obj:
            self._active_connections[obj] = 1
        return conn

    async def return_to_pool(self, conn: SMTP, obj: Optional[AsyncSMTPConnection] = None):
        self.connections.task_done()
        self.loop.create_task(self.connections.put(conn))
        if obj:
            del self._active_connections[obj]

    async def reconnect(self, conn: SMTP):
        if not conn.is_connected:
            tries = 3
            while tries:
                try:
                    await conn.connect()
                    if conn.is_connected:
                        break
                except SMTPConnectError:
                    logger.debug('error re-establishing ', self.LOG_NAME)
                    tries -= 1
        # remove broken conn from queue and add new conn
        if conn.is_connected:
            self.connections.task_done()
            await self.connections.put(conn)
        else:
            self.loop.create_task(self.create_connection())

    async def create_connection(self):
        conn = SMTP(
            hostname=SMTPConfig.EMAIL_HOST, username=SMTPConfig.EMAIL_HOST_USER,
            password=SMTPConfig.EMAIL_HOST_PASSWORD, port=SMTPConfig.EMAIL_PORT,
            use_tls=SMTPConfig.EMAIL_USE_TLS,
            source_address=SMTPConfig.LOCALHOST_NAME,
            tls_context=ssl.create_default_context(cafile=certifi.where())
        )

        await conn.connect()
        logger.debug("created connection", self.LOG_NAME)
        await self.connections.put(conn)
