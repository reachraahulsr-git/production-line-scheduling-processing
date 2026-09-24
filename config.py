"""
Production Line Resource Scheduling System - Configuration
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE_PATH = os.path.join(BASE_DIR, "database", "production.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")

JAVA_SRC_DIR = os.path.join(BASE_DIR, "java_engine", "src")
JAVA_BIN_DIR = os.path.join(BASE_DIR, "java_engine", "bin")

JAVA_IPC_HOST = "127.0.0.1"
JAVA_IPC_PORT = 5050

SECRET_KEY = os.environ.get("SECRET_KEY", "prod-scheduling-sys-secret-key-2026")
DEBUG = True
