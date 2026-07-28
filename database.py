import sqlite3

DB_NAME = "movie_bot.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Users Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            points INTEGER DEFAULT 0
        )
    """
    )

    # Movie Batches Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS movie_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, referrer_id, points) VALUES (?, ?, 0)",
            (user_id, referrer_id),
        )

        if referrer_id and referrer_id != user_id:
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
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0


def deduct_point(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET points = points - 1 WHERE user_id = ? AND points > 0",
        (user_id,),
    )
    conn.commit()
    conn.close()
    
