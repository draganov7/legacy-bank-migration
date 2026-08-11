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
        CREATE OR REPLACE TABLE core.dim_account AS

        SELECT
            account_id,
            account_number,
            customer_id,
            branch_id,
            account_type,
            currency_code,
            opened_date,
            closed_date,
            account_status,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM staging.stg_account
        """
    )

    row_count = con.execute(
        """
        SELECT COUNT(*)
        FROM core.dim_account
        """
    ).fetchone()[0]

    duplicate_count = con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT account_id
            FROM core.dim_account
            GROUP BY account_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """
    ).fetchone()[0]

    unresolved_customers = con.execute(
        """
        SELECT COUNT(*)
        FROM core.dim_account AS account
        LEFT JOIN core.dim_customer AS customer
            ON account.customer_id = customer.customer_id
        WHERE customer.customer_id IS NULL
        """
    ).fetchone()[0]

    if duplicate_count != 0:
        con.close()
        raise RuntimeError(
            f"Duplicate account IDs found: {duplicate_count}"
        )

    if unresolved_customers != 0:
        con.close()
        raise RuntimeError(
            f"Accounts with unresolved customers: "
            f"{unresolved_customers}"
        )

    con.close()

    print(f"Core accounts: {row_count}")
    print("Duplicate account IDs: 0")
    print("Accounts with unresolved customers: 0")


if __name__ == "__main__":
    main()