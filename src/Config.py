import os

IN_DOCKER_CONTAINER = os.environ.get("IN_DOCKER_CONTAINER", False)
LOCALHOST_NAME = 'docker.for.mac.localhost' if IN_DOCKER_CONTAINER else 'localhost'
PORT = "5454"
USERNAME = 'KoboNotifyAdmin'
PASSWORD = "PasswordForKoboNotifyAdmin"
DB_NAME = "KoboNotifyDB"
DRIVER = "postgresql+asyncpg"
SQLALCHEMY_DATABASE_URI = f"{DRIVER}://{USERNAME}:{PASSWORD}@{LOCALHOST_NAME}:{PORT}/{DB_NAME}"


DEFAULT_TRIGGER_OPTIONS = {
    'output_file': 'triggers.sql',
    'triggers': ['update', 'insert', 'delete'],
    'trigger_names': {'update': '', 'insert': '', 'delete': ''}
}