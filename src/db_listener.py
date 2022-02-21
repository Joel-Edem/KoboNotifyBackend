import json

from logger import logger
from src.generate_triggers_sql import generate_trigger_sql

EVENTS = ('insert',)
service_name = 'outbound_msg'
table_name = 'UserMessages_outgoingmessage'


async def handle_notify(*args):
    """
    :param args: conn=None, obj_id=None, event_type=None, new_data={},
    :return:
    """

    new_data = json.loads(args[-1])
    data = new_data['new_data']


# noinspection PyProtectedMember
class DbListener:

    def __init__(self, _db, callback):
        self.connection = None
        self.cursor = None
        self.db = _db
        self.callback = callback

    async def connect_to_db(self):
        logger.debug("connecting to data base" ,'blue')
        await self.db.init()
        self.connection = await self.db._engine.connect()
        _raw_conn = await self.connection.get_raw_connection()
        self.cursor = _raw_conn.driver_connection
        logger.debug("connected to database")

    async def _configure_db(self):
        logger.debug("configuring database")
        sql = generate_trigger_sql(service_name, table_name)
        await self.cursor.execute(sql)
        logger.debug("database configured ")

    async def add_handler(self):
        logger.debug("adding handlerS")
        for event in EVENTS:
            await self.cursor.execute(f'LISTEN {service_name}_{event};')
            await self.cursor.add_listener(f"{service_name}_{event}", self.callback)
        logger.debug("handlers added ")

    async def start(self):
        logger.debug("Starting db listener")
        await self.connect_to_db()
        await self._configure_db()
        await self.add_handler()
        logger.debug("db listener started")

    async def stop(self):
        await self.connection.close()
        await self.db.stop()
        logger.debug('db listener stopped', 'red')
