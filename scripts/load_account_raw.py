import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv


LANDING_DIRECTORY = Path("data/landing/core/account")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch-id",
        required=True,
    )

    args = parser.parse_args()

    load_dotenv()

    duckdb_path = os.getenv("DUCKDB_PATH")

    if not duckdb_path:
        raise RuntimeError("DUCKDB_PATH is not set")

    parquet_path = (
        LANDING_DIRECTORY
        / args.batch_id
        / "account.parquet"
    )

    if not parquet_path.exists():
        raise RuntimeError(
            f"Parquet file does not exist: {parquet_path}"
        )

    ingested_at = datetime.now(timezone.utc)

    con = duckdb.connect(duckdb_path)

    con.execute(
        """
        CREATE SCHEMA IF NOT EXISTS raw
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS raw.raw_account (
            account_id BIGINT,
            account_number VARCHAR,
            customer_id BIGINT,
            branch_id BIGINT,
            account_type VARCHAR,
            currency_code VARCHAR,
            opened_date DATE,
            closed_date DATE,
            status VARCHAR,
            created_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ,

            migration_batch_id VARCHAR,
            source_system VARCHAR,
            source_table VARCHAR,
            source_record_key VARCHAR,
            source_updated_at TIMESTAMPTZ,
            ingested_at TIMESTAMPTZ,
            record_hash VARCHAR,
            schema_version VARCHAR,
            is_deleted BOOLEAN
        )
        """
    )

    already_loaded = con.execute(
        """
        SELECT COUNT(*)
        FROM raw.raw_account
        WHERE migration_batch_id = ?
        """,
        [args.batch_id],
    ).fetchone()[0]

    if already_loaded > 0:
        con.close()

        raise RuntimeError(
            f"Batch already loaded: {args.batch_id}"
        )

    con.execute(
        """
        INSERT INTO raw.raw_account

        SELECT
            account_id,
            account_number,
            customer_id,
            branch_id,
            account_type,
            currency_code,
            opened_date,
            closed_date,
            status,
            created_at,
            updated_at,

            ? AS migration_batch_id,

            'neon_postgresql'
                AS source_system,

            'core.account'
                AS source_table,

            CAST(account_id AS VARCHAR)
                AS source_record_key,

            updated_at
                AS source_updated_at,

            ?
                AS ingested_at,

            sha256(
                concat_ws(
                    '|',
                    CAST(account_id AS VARCHAR),
                    account_number,
                    CAST(customer_id AS VARCHAR),
                    CAST(branch_id AS VARCHAR),
                    account_type,
                    currency_code,
                    CAST(opened_date AS VARCHAR),
                    COALESCE(
                        CAST(closed_date AS VARCHAR),
                        ''
                    ),
                    status
                )
            ) AS record_hash,

            '1.0'
                AS schema_version,

            FALSE
                AS is_deleted

        FROM read_parquet(?)
        """,
        [
            args.batch_id,
            ingested_at,
            str(parquet_path),
        ],
    )

    loaded_rows = con.execute(
        """
        SELECT COUNT(*)
        FROM raw.raw_account
        WHERE migration_batch_id = ?
        """,
        [args.batch_id],
    ).fetchone()[0]

    con.close()

    print(f"Batch ID: {args.batch_id}")
    print(f"Rows loaded: {loaded_rows}")
    print(f"DuckDB: {duckdb_path}")
    print("Target table: raw.raw_account")


if __name__ == "__main__":
    main()