import os
from dataclasses import dataclass

IN_DOCKER_CONTAINER = os.environ.get("IN_DOCKER_CONTAINER", False)
LOCALHOST_NAME = 'docker.for.mac.localhost' if IN_DOCKER_CONTAINER else 'localhost'
PORT = "5454"
USERNAME = 'KoboNotifyAdmin'
PASSWORD = "PasswordForKoboNotifyAdmin"
DB_NAME = "KoboNotifyDB"
DRIVER = "postgresql+asyncpg"
SQLALCHEMY_DATABASE_URI = f"{DRIVER}://{USERNAME}:{PASSWORD}@{LOCALHOST_NAME}:{PORT}/{DB_NAME}"
SMS_Endpoint = "https://api.mnotify.com/api/sms/quick"
# "https://apps.mnotify.net/smsapi"
SMS_SENDER_ID = ""
SMS_API_KEY = ""

"""
        MNOTIFY RESPONSE CODES:
    1000 = Message submitted successful
    1002 = SMS sending failed
    1003 = insufficient balance
    1004 = invalid API key
    1005 = invalid Phone Number
    1006 = invalid Sender ID. Sender ID must not be more than 11 Characters. Characters include white space.
    1007 = Message scheduled for later delivery
    1008 = Empty Message
    1009 = Empty from date and to date
    1010 = No messages has been sent on the specified dates using the specified api key
    1011 = Numeric Sender IDs are not allowed
    1012 = Sender ID is not registered. Please contact our support team via 
    senderids@mnotify.com or call 0541509394 for assistance

"""

DEFAULT_TRIGGER_OPTIONS = {
    'output_file': 'triggers.sql',
    'triggers': ['update', 'insert', 'delete'],
    'trigger_names': {'update': '', 'insert': '', 'delete': ''}
}


@dataclass()
class SMTPConfig:
    EMAIL_HOST: str = 'smtp.gmail.com'
    EMAIL_HOST_USER: str = os.environ['dev_email']
    EMAIL_HOST_PASSWORD: str = os.environ['dev_email_pw']
    EMAIL_PORT: int = 465
    EMAIL_USE_TLS: bool = True
    LOCALHOST_NAME: str = f'0.0.0.0'
