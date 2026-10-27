"""
Database connection and execution layer.
Pure raw SQL - no ORMs, no query builders.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recruiter_bot.db")
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed.sql")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a new SQLite database connection with row factory enabled."""
    path = db_path or DB_FILE
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the database schema using raw SQL DDL from schema.sql."""
    conn = get_db_connection(db_path)
    try:
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            ddl_script = f.read()
        conn.executescript(ddl_script)
        conn.commit()
    finally:
        conn.close()


def seed_db(db_path: Optional[str] = None) -> None:
    """Seeds the database with candidates and jobs using raw SQL from seed.sql."""
    # First ensure schema exists
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            seed_script = f.read()
        conn.executescript(seed_script)
        conn.commit()
    finally:
        conn.close()


def query_raw(sql: str, params: Tuple[Any, ...] = (), db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Executes a raw SQL query and returns results as a list of dictionaries."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def execute_raw(sql: str, params: Tuple[Any, ...] = (), db_path: Optional[str] = None) -> int:
    """Executes a raw SQL statement (INSERT, UPDATE, DELETE) and returns the last row ID."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
