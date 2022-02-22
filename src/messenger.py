import asyncio
import datetime
import enum
import json
from asyncio.queues import Queue
from dataclasses import dataclass
from typing import Optional

import aiohttp
import aiosmtplib
from jinja2 import Template

from logger import logger
from src import env
from src.Config import SMTPConfig
from src.db import AsyncDatabaseSession
from src.smtp_connection import AsyncSMTPConnectionPool
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy import text, String

SENDER_PHONE_NUM = ""


# noinspection PyShadowingBuiltins
@dataclass
class SMS:
    id: int
    recipient: str
    # message: str
    MESSAGE_CHUNKS: list[str]
    CHUNK_SIZE: int = 140
    TOTAL_SENT: int = 0

    def __init__(self, id: int, recipient, message):
        self.id = id
        self.recipient = recipient
        # self.message = message
        self.MESSAGE_CHUNKS = self._prepare_message_chunks(message)

    def _prepare_message_chunks(self, message: str) -> list[str]:
        msg = message
        chunks: [str] = []
        messages: [str] = []
        while len(msg) > self.CHUNK_SIZE:
            chunk_end = self.CHUNK_SIZE - 5
            chunk: str = msg[:chunk_end]
            if not chunk.endswith((" ", ". ")):
                tokens = chunk.split()[:-1]
                chunk = " ".join(tokens)
                chunk_end = len(chunk)
            chunks.append(chunk)
            msg = msg[chunk_end:]
        chunks.append(msg)

        num_chunks = len(chunks)
        if num_chunks > 1:
            for num, chunk in enumerate(chunks):
                if num == 0:
                    messages.append(
                        chunk + f" {num + 1}/{num_chunks}"
                    )
                else:
                    messages.append(
                        f"{num + 1}/{num_chunks} " + chunk
                    )
        else:
            messages.append(chunks[0])
        return messages


@dataclass
class Email:
    id: int
    recipient: str
    message: str
    subject: str
    template_name: Optional[str] = None

    # template: Template

    @property
    async def template(self) -> Optional[Template]:
        loop = asyncio.get_running_loop()
        if self.template_name:
            return await loop.run_in_executor(None, env.get_template(self.template_name))

    async def get_message(self) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["From"] = SMTPConfig.EMAIL_HOST_USER
        message["To"] = self.recipient
        message["Subject"] = self.subject
        plain_text_message = MIMEText(self.message, "plain", "utf-8")
        message.attach(plain_text_message)

        if self.template_name:
            template = await self.template
            html_str = await template.render_async(message=self.message)
            html_message = MIMEText(html_str, "html", "utf-8")
            message.attach(html_message)
        return message


class MessageStatus(enum.Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class Messenger:

    def __init__(self, msg_queue: Queue, _db: AsyncDatabaseSession, _loop=None):
        """
        This class will watch a queue for messages consume messages from queue
        """
        self.loop = _loop or asyncio.get_event_loop()
        self.msq_queue = msg_queue
        self.smtp_conns = AsyncSMTPConnectionPool(max_connections=12, loop=self.loop)
        self.http_conn = None
        self.db = _db
        self.max_workers = 12
        self.curr_workers = 0
        self.consumer = None
        self.running = False

    async def send_sms_chunk(self, msg, phone_num) -> bool:  # todo: NOT IMPLEMENTED
        """
        make request to service and return ture if successful else false
        :param msg:
        :param phone_num:
        :return:
        """
        logger.error('NOT IMPLEMENTED', 'red')
        return True

    async def process_messages(self):

        while self.running:
            if self.curr_workers < self.max_workers:
                data = await self.msq_queue.get()
                self.loop.create_task(self.process_message(data))

    async def process_message(self, data):
        """
        consumes email or sms obj from queues and process it.
        writes back to database after processing
        :return:
        """
        try:
            if data['send_via'] == "EMAIL":
                message = await self.prepare_email(data)
                res = await self.send_email(message)
            else:
                message = await self.prepare_sms(data)
                res = await self.send_sms(message)

            await self.change_message_status(message.id, res)
            self.msq_queue.task_done()
        finally:
            self.curr_workers -= 1

    async def change_message_status(self, msg_id: int, status: MessageStatus.SENDING):
        """
        Set message status when processing and after completion
        :param msg_id:
        :param status:
        :return:
        """
        delivered_on = f"delivered_on={datetime.datetime.now()}"
        sql = f"""
                    UPDATE "UserMessages_outgoingmessage"
                    WHERE id=:msg_id
                    SET status={status.name} 
                        {delivered_on if status == MessageStatus.DELIVERED else ''}
                """

        async with self.db.session() as session:
            t = text(sql).bindparams(msg_id=msg_id)
            res = await session.execute(t)

    async def send_sms(self, sms: SMS) -> MessageStatus:
        retries = 0
        msgs_tasks = [self.send_sms_chunk(chunk, sms.recipient) for chunk in sms.MESSAGE_CHUNKS]
        while (sms.TOTAL_SENT < len(sms.MESSAGE_CHUNKS)) and (retries < 3):
            msg_status = await asyncio.gather(*[asyncio.create_task(t) for t in msgs_tasks])
            completed = [idx for idx, res in enumerate(msg_status) if res]
            sms.TOTAL_SENT += len(completed)
            if sms.TOTAL_SENT == len(sms.MESSAGE_CHUNKS):
                return MessageStatus.DELIVERED
            msgs_tasks = [t for idx, t in enumerate(msgs_tasks) if idx not in completed]
            retries += 1
        return MessageStatus.FAILED

    async def send_email(self, email: Email) -> MessageStatus:
        retries = 0
        msg, conn = await asyncio.gather(email.get_message(), self.smtp_conns.get_connection())
        while retries < 3:
            try:
                await conn.send_message(msg)
                return MessageStatus.DELIVERED
            except aiosmtplib.SMTPException as e:
                logger.error(e, 'red')
                retries += 1
        return MessageStatus.FAILED

    async def handle_notify(self, *args):
        """
        :param args: conn=None, obj_id=None, event_type=None, new_data={},
        :return:
        """

        new_data = json.loads(args[-1])
        data = new_data['new_data']

        if data['send_via'] not in ["EMAIL", "PHONE"]:
            raise ValueError(f"Invalid delivery method set. Expected EMAIL or PHONE got {data['send_via']}")

        self.loop.create_task(self.change_message_status(data['id'], MessageStatus.SENDING.name))
        await self.msq_queue.put(data)

    async def load_message(self, asset_id, msg_type) -> str:
        """

        :param msg_type: column names 'PHONE' or 'EMAIL'
        :param asset_id:
        :return:
        """
        _msg_type = "sms_message" if msg_type == 'PHONE' else 'email_message'
        sql = f"""
            SELECT "UserAssets_userasset".{_msg_type}
            FROM "UserAssets_userasset" 
            WHERE "UserAssets_userasset"."asset_id"=:asset_id
        """

        async with self.db.session() as session:
            t = text(sql).bindparams(asset_id=asset_id).columns(**{f"{_msg_type}": String})
            res = await session.execute(t)
            return res.get(_msg_type)

    async def prepare_sms(self, data) -> SMS:
        message = await self.load_message(data['asset_id'], msg_type="PHONE")
        msg = SMS(
            id=data['id'],
            recipient=data['recipient'],
            message=message
        )
        return msg

    async def prepare_email(self, data) -> Email:

        message = await self.load_message(data['asset_id'], msg_type="EMAIL")
        email = Email(
            id=data['id'],
            recipient=data['recipient'],
            message=message,
            subject="New Message Alert" if data["message_type"] == "NEW" else "Update Alert"
        )
        print("email prepped")
        return email

    async def start(self):
        self.running = True
        self.http_conn = aiohttp.ClientSession()
        await asyncio.gather(
            self.smtp_conns.start(),  # create smtp connection and connection for
            self.db.init()
        )
        self.consumer = self.loop.create_task(self.process_messages())

    async def stop(self):
        self.running = False
        self.consumer.cancel()
        cur_tasks = [t for t in asyncio.all_tasks(self.loop) if t.get_coro().__name__ not in (
                'close', 'stop', 'process_messages')]
        if cur_tasks:
            await asyncio.wait(cur_tasks, timeout=60)
        await asyncio.gather(
            self.http_conn.close(),
            self.smtp_conns.stop(),
        )


