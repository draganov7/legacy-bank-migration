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
        CREATE OR REPLACE TABLE core.fct_transaction AS

        SELECT
            transaction_id,
            source_account_id,
            destination_account_id,
            transaction_timestamp_utc,
            transaction_type,
            transaction_amount,
            currency_code,
            payment_channel,
            is_aml_flagged,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM staging.stg_transaction
        """
    )

    staging_count = con.execute(
        """
        SELECT COUNT(*)
        FROM staging.stg_transaction
        """
    ).fetchone()[0]

    core_count = con.execute(
        """
        SELECT COUNT(*)
        FROM core.fct_transaction
        """
    ).fetchone()[0]

    duplicate_count = con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT transaction_id
            FROM core.fct_transaction
            GROUP BY transaction_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """
    ).fetchone()[0]

    missing_source_accounts = con.execute(
        """
        SELECT COUNT(*)
        FROM core.fct_transaction AS t
        LEFT JOIN core.dim_account AS a
            ON t.source_account_id = a.account_id
        WHERE a.account_id IS NULL
        """
    ).fetchone()[0]

    missing_destination_accounts = con.execute(
        """
        SELECT COUNT(*)
        FROM core.fct_transaction AS t
        LEFT JOIN core.dim_account AS a
            ON t.destination_account_id = a.account_id
        WHERE a.account_id IS NULL
        """
    ).fetchone()[0]

    if staging_count != core_count:
        con.close()
        raise RuntimeError(
            "Staging/core transaction counts do not match: "
            f"{staging_count} != {core_count}"
        )

    if duplicate_count != 0:
        con.close()
        raise RuntimeError(
            f"Duplicate transaction IDs found: {duplicate_count}"
        )

    if missing_source_accounts != 0:
        con.close()
        raise RuntimeError(
            f"Missing source accounts: {missing_source_accounts}"
        )

    if missing_destination_accounts != 0:
        con.close()
        raise RuntimeError(
            "Missing destination accounts: "
            f"{missing_destination_accounts}"
        )

    con.close()

    print(f"Staging transactions: {staging_count}")
    print(f"Core transactions: {core_count}")
    print("Duplicate transaction IDs: 0")
    print("Missing source accounts: 0")
    print("Missing destination accounts: 0")
    print("Transaction fact build verified successfully")


if __name__ == "__main__":
    main()