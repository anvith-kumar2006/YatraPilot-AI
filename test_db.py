import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

try:
    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), version();")
            result = cur.fetchone()

            print("YatraPilot AI Database Connected!")
            print("Database:", result[0])

except Exception as error:
    print("Connection failed:", error)