import os

import duckdb
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    duckdb_path = os.getenv("DUCKDB_PATH")

    if not duckdb_path:
        raise RuntimeError("DUCKDB_PATH is not set")

    con = duckdb.connect(duckdb_path)

    con.execute("CREATE SCHEMA IF NOT EXISTS core")

    con.execute(
        """
        CREATE OR REPLACE TABLE core.dim_customer AS

        SELECT
            customer_id,
            customer_number,
            customer_name,
            date_of_birth,
            email_normalised,
            phone,
            country_code,
            kyc_status,
            customer_status,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM staging.stg_customer
        """
    )

    row_count = con.execute(
        """
        SELECT COUNT(*)
        FROM core.dim_customer
        """
    ).fetchone()[0]

    duplicate_count = con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT customer_id
            FROM core.dim_customer
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """
    ).fetchone()[0]

    if duplicate_count != 0:
        con.close()
        raise RuntimeError(
            f"Duplicate customer IDs found: {duplicate_count}"
        )

    con.close()

    print(f"Core customers: {row_count}")
    print("Duplicate customer IDs: 0")


if __name__ == "__main__":
    main()