import sqlite3
import os
from flask import g
# --- Database Functions ---
DATABASE = "chat.db"

def init_db():
    if not os.path.exists(DATABASE):
        with sqlite3.connect(DATABASE) as conn:
            # Assuming schema.sql exists and is correctly defined
            with open("schema.sql", "r") as f:
                conn.executescript(f.read())

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
