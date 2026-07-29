import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


DDL_DIRECTORY = Path("sql/source_ddl")


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    sql_files = sorted(DDL_DIRECTORY.glob("*.sql"))

    if not sql_files:
        raise RuntimeError(f"No SQL files found in {DDL_DIRECTORY}")

    with psycopg.connect(database_url) as connection:
        for sql_file in sql_files:
            sql = sql_file.read_text(encoding="utf-8")

            print(f"Applying {sql_file.name}")

            with connection.cursor() as cursor:
                cursor.execute(sql)

        connection.commit()

    print("Source database DDL applied successfully")


if __name__ == "__main__":
    main()