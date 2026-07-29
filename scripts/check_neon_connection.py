import os

import psycopg
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    version()
                """
            )
            database_name, username, postgres_version = cursor.fetchone()

    print(f"Connected database: {database_name}")
    print(f"Connected user: {username}")
    print(f"PostgreSQL version: {postgres_version}")


if __name__ == "__main__":
    main()