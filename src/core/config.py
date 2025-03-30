import os
import json
from dotenv import load_dotenv

# Load .env but do NOT override existing environment variables
# Variables set by Docker Compose (like DB_HOST) should take precedence.
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_INIT = os.getenv("DB_INIT", "false").lower() == "true"
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USER = os.getenv("SMTP_USER")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = os.getenv("REDIS_DB")
REDIS_SSL = os.getenv("REDIS_SSL")

SECRET = os.getenv("SECRET")
# import os, base64
# print(base64.urlsafe_b64encode(os.urandom(32)).decode())

# CORS settings
CORS_ORIGINS = json.loads(os.getenv("CORS_ORIGINS", "[]"))
CORS_HEADERS = json.loads(os.getenv("CORS_HEADERS", "[]"))
CORS_METHODS = json.loads(os.getenv("CORS_METHODS", "[]"))
CORS_CREDENTIALS = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"

# Планировщик
SCHEDULER_CLEANUP_INTERVAL = int(
    os.getenv("SCHEDULER_CLEANUP_INTERVAL", "1")
)  # minutes

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
