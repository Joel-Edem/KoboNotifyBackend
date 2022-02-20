import asyncio

from src.db import AsyncDatabaseSession
from src.db_listener import DbListener, handle_notify

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    db = AsyncDatabaseSession()
    db_listener = DbListener(db, handle_notify)
    try:
        loop.create_task(db_listener.start())
        loop.run_forever()
    except KeyboardInterrupt:
        print("shutting down")
        pass
    finally:
        # print("shutting down")
        loop.run_until_complete(asyncio.shield(db_listener.stop()))
        loop.close()
        # print("Db listener stopped")
