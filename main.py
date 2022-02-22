import asyncio

from logger import logger
from src.db import AsyncDatabaseSession
from src.db_listener import DbListener, handle_notify
from src.messenger import Messenger

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    db = AsyncDatabaseSession()
    message_queue = asyncio.queues.Queue()
    message_service = Messenger(msg_queue=message_queue, _db=db, _loop=loop)
    db_listener = DbListener(db, message_service.handle_notify)


    try:
        logger.debug(str((" * " * 6) + "Starting Service" + (" * " * 6)), 'green')
        loop.create_task(db_listener.start())
        loop.create_task(message_service.start())
        logger.debug((" * " * 6) + "Service Started" + (" * " * 6), 'green')
        loop.run_forever()
    except KeyboardInterrupt:
        logger.debug("shutting down")
    finally:
        logger.debug((" * " * 6) + "Stopping Service" + (" * " * 6), "green")

        loop.run_until_complete(asyncio.shield(db_listener.stop()))
        loop.run_until_complete(asyncio.shield(message_service.stop()))
        loop.close()
        logger.debug((" * " * 6) + "Service Stopped" + (" * " * 6), 'green')

# todo load and process un processed  messages on startup
