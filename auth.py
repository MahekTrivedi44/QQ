import bcrypt
from db import get_db
import re
import sqlite3

# --- Auth Functions ---
def create_user(username, password):
    # Password policy checks
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?:{}|<>)."

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        db.commit()
        return True, "User created successfully."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    except Exception as e:
        print(f"Error creating user: {e}")
        db.rollback()
        return False, "Server error during user creation."

def verify_user(username, password):
    db = get_db()
    user = db.execute("SELECT id, password FROM users WHERE username = ?", (username,)).fetchone()
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        return user["id"]
    return None