# db_config.py
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()  # loads .env

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=int(os.getenv("DB_PORT", 5432))
    )
    return conn

# helper to fetch dict results
def get_dict_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)
