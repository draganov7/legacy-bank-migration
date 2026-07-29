import os

import psycopg
from dotenv import load_dotenv


EXPECTED_TABLES = {
    "branch",
    "customer",
    "account",
}

EXPECTED_FOREIGN_KEYS = {
    "fk_account_customer",
    "fk_account_branch",
}


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'core'
                ORDER BY table_name
                """
            )
            tables = {row[0] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'core'
                  AND table_name = 'account'
                  AND constraint_type = 'FOREIGN KEY'
                ORDER BY constraint_name
                """
            )
            foreign_keys = {row[0] for row in cursor.fetchall()}

    missing_tables = EXPECTED_TABLES - tables
    missing_foreign_keys = EXPECTED_FOREIGN_KEYS - foreign_keys

    if missing_tables:
        raise RuntimeError(f"Missing core tables: {sorted(missing_tables)}")

    if missing_foreign_keys:
        raise RuntimeError(
            f"Missing account foreign keys: {sorted(missing_foreign_keys)}"
        )

    print("Core tables:")
    for table in sorted(EXPECTED_TABLES):
        print(f"  - core.{table}")

    print("Account foreign keys:")
    for foreign_key in sorted(EXPECTED_FOREIGN_KEYS):
        print(f"  - {foreign_key}")

    print("Core source tables verified successfully")


if __name__ == "__main__":
    main()