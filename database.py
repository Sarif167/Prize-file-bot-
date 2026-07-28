# database.py

import sqlite3
from config import DB_NAME


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Users Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            referred_by INTEGER
        )
    """
    )

    # Batch Files Table (Store multiple files for a single movie code)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS movie_batches (
            movie_id TEXT,
            file_id TEXT
        )
    """
    )

    conn.commit()
    conn.close()


def add_user(user_id, referrer_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, points, referred_by) VALUES (?, 0, ?)",
            (user_id, referrer_id),
        )
        if referrer_id and referrer_id != user_id:
            # Add 1 Point/Credit to referrer
            cursor.execute(
                "UPDATE users SET points = points + 1 WHERE user_id = ?",
                (referrer_id,),
            )
        conn.commit()

    conn.close()


def get_points(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0


def deduct_point(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET points = points - 1 WHERE user_id = ?", (user_id,)
    )
    conn.commit()
    conn.close()
  
