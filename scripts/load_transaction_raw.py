import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv


LANDING_DIRECTORY = Path(
    "data/landing/payments/bank_transaction"
)


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
        / "bank_transaction.parquet"
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
        CREATE TABLE IF NOT EXISTS raw.raw_transaction (
            transaction_id BIGINT,
            source_account_id BIGINT,
            destination_account_id BIGINT,
            transaction_ts TIMESTAMPTZ,
            transaction_type VARCHAR,
            amount DECIMAL(18, 2),
            currency_code VARCHAR,
            payment_channel VARCHAR,
            aml_flag BOOLEAN,
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
        FROM raw.raw_transaction
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
        INSERT INTO raw.raw_transaction

        SELECT
            transaction_id,
            source_account_id,
            destination_account_id,
            transaction_ts,
            transaction_type,
            amount,
            currency_code,
            payment_channel,
            aml_flag,
            created_at,
            updated_at,

            ? AS migration_batch_id,

            'neon_postgresql'
                AS source_system,

            'payments.bank_transaction'
                AS source_table,

            CAST(transaction_id AS VARCHAR)
                AS source_record_key,

            updated_at
                AS source_updated_at,

            ?
                AS ingested_at,

            sha256(
                concat_ws(
                    '|',
                    CAST(transaction_id AS VARCHAR),
                    CAST(source_account_id AS VARCHAR),
                    CAST(destination_account_id AS VARCHAR),
                    CAST(transaction_ts AS VARCHAR),
                    transaction_type,
                    CAST(amount AS VARCHAR),
                    currency_code,
                    payment_channel,
                    CAST(aml_flag AS VARCHAR)
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
        FROM raw.raw_transaction
        WHERE migration_batch_id = ?
        """,
        [args.batch_id],
    ).fetchone()[0]

    con.close()

    print(f"Batch ID: {args.batch_id}")
    print(f"Rows loaded: {loaded_rows}")
    print(f"DuckDB: {duckdb_path}")
    print("Target table: raw.raw_transaction")


if __name__ == "__main__":
    main()