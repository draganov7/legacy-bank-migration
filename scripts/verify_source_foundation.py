import os

import psycopg
from dotenv import load_dotenv


EXPECTED_SCHEMAS = {"core", "payments", "control"}

EXPECTED_CONTROL_TABLES = {
    "migration_batch",
    "table_run",
    "source_extract_control",
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
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN ('core', 'payments', 'control')
                ORDER BY schema_name
                """
            )
            schemas = {row[0] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'control'
                ORDER BY table_name
                """
            )
            control_tables = {row[0] for row in cursor.fetchall()}

    missing_schemas = EXPECTED_SCHEMAS - schemas
    missing_tables = EXPECTED_CONTROL_TABLES - control_tables

    if missing_schemas:
        raise RuntimeError(f"Missing schemas: {sorted(missing_schemas)}")

    if missing_tables:
        raise RuntimeError(f"Missing control tables: {sorted(missing_tables)}")

    print("Schemas:")
    for schema in sorted(schemas):
        print(f"  - {schema}")

    print("Control tables:")
    for table in sorted(control_tables):
        print(f"  - control.{table}")

    print("Source foundation verified successfully")


if __name__ == "__main__":
    main()