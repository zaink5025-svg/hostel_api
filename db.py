"""
db.py - everything related to talking to MySQL.

This file replaces the "FILE MANAGEMENT" section of your old main.py
(read_all, write_all, add_line, find_line, update_line, delete_line ...).
Now we simply run SQL instead of editing text files.
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from mysql.connector import pooling

# Read DB_HOST, DB_USER, ... from the .env file
load_dotenv()

_pool = None


def _get_pool():
    """Create the connection pool the first time it is needed."""
    global _pool

    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="hostel_pool",
            pool_size=5,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "hostel_db"),
        )

    return _pool


@contextmanager
def db_cursor():
    """
    Use it like this:

        with db_cursor() as cur:
            cur.execute("SELECT * FROM students WHERE id = %s", (5,))
            row = cur.fetchone()

    - If everything works, the changes are saved (commit).
    - If anything fails, ALL changes inside the block are undone (rollback).
      This is important when one action changes two tables
      (for example: allocation + bed status).
    """
    connection = _get_pool().get_connection()
    cursor = connection.cursor(dictionary=True)  # rows come back as dicts

    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()  # returns the connection to the pool


def query_all(sql, params=None):
    """Run a SELECT and return a list of rows."""
    with db_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def query_one(sql, params=None):
    """Run a SELECT and return one row (or None)."""
    with db_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(sql, params=None):
    """Run INSERT / UPDATE / DELETE. Returns the new row id for INSERT."""
    with db_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.lastrowid