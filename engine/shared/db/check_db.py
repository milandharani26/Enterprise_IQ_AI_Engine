from engine.shared.db.session import sync_engine
from sqlalchemy import text
import sys

def check_db():
    try:
        with sync_engine.connect() as conn:
            res = conn.execute(text('SELECT 1'))
            if res.fetchone():
                print("Database Connected Successfully!")
                sys.exit(0)
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_db()
