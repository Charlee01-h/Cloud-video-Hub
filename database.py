import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path="database.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_premium INTEGER DEFAULT 0,
                expiry_date TEXT,
                daily_limit INTEGER DEFAULT 5
            )
        """)
        self.conn.commit()

    def add_user(self, user_id):
        self.cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_user_limit(self, user_id):
        self.cursor.execute("SELECT daily_limit FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 5

    def decrease_limit(self, user_id):
        self.cursor.execute("UPDATE users SET daily_limit = daily_limit - 1 WHERE user_id = ? AND daily_limit > 0", (user_id,))
        self.conn.commit()

    def check_limit_exceeded(self, user_id):
        self.cursor.execute("SELECT daily_limit FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] <= 0 if result else False

    def set_premium(self, user_id, days):
        expiry_date = datetime.now() + timedelta(days=days)
        self.cursor.execute("UPDATE users SET is_premium = 1, expiry_date = ? WHERE user_id = ?", (expiry_date.strftime("%Y-%m-%d"), user_id))
        self.conn.commit()

    def get_subscription_expiry(self, user_id):
        self.cursor.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result and result[0] else None

    def reset_daily_limits(self):
        self.cursor.execute("UPDATE users SET daily_limit = 5 WHERE is_premium = 0")
        self.conn.commit()

    def check_expired_subscriptions(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("UPDATE users SET is_premium = 0, expiry_date = NULL WHERE expiry_date <= ?", (today,))
        self.conn.commit()

    def close(self):
        self.conn.close()

# Example usage
if __name__ == "__main__":
    db = Database()
    db.reset_daily_limits()
    db.check_expired_subscriptions()
