import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dotenv import load_dotenv


LANDING_DIRECTORY = Path("data/landing/core/customer")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    load_dotenv()

    duckdb_path = os.getenv("DUCKDB_PATH")

    if not duckdb_path:
        raise RuntimeError("DUCKDB_PATH is not set")

    parquet_path = (
        LANDING_DIRECTORY
        / args.batch_id
        / "customer.parquet"
    )

    if not parquet_path.exists():
        raise RuntimeError(
            f"Parquet file does not exist: {parquet_path}"
        )

    ingested_at = datetime.now(timezone.utc)

    connection = duckdb.connect(duckdb_path)

    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS raw.raw_customer (
            customer_id BIGINT,
            customer_number VARCHAR,
            full_name VARCHAR,
            date_of_birth DATE,
            email VARCHAR,
            phone VARCHAR,
            address_line_1 VARCHAR,
            address_line_2 VARCHAR,
            city VARCHAR,
            state VARCHAR,
            postal_code VARCHAR,
            country_code VARCHAR,
            kyc_status VARCHAR,
            customer_status VARCHAR,
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

    already_loaded = connection.execute(
        """
        SELECT COUNT(*)
        FROM raw.raw_customer
        WHERE migration_batch_id = ?
        """,
        [args.batch_id],
    ).fetchone()[0]

    if already_loaded > 0:
        connection.close()
        raise RuntimeError(
            f"Batch already loaded: {args.batch_id}"
        )

    connection.execute(
        """
        INSERT INTO raw.raw_customer
        SELECT
            customer_id,
            customer_number,
            full_name,
            date_of_birth,
            email,
            phone,
            address_line_1,
            address_line_2,
            city,
            state,
            postal_code,
            country_code,
            kyc_status,
            customer_status,
            created_at,
            updated_at,

            ? AS migration_batch_id,
            'neon_postgresql' AS source_system,
            'core.customer' AS source_table,
            CAST(customer_id AS VARCHAR) AS source_record_key,
            updated_at AS source_updated_at,
            ? AS ingested_at,

            sha256(
                concat_ws(
                    '|',
                    CAST(customer_id AS VARCHAR),
                    customer_number,
                    full_name,
                    CAST(date_of_birth AS VARCHAR),
                    COALESCE(email, ''),
                    COALESCE(phone, ''),
                    country_code,
                    kyc_status,
                    customer_status
                )
            ) AS record_hash,

            '1.0' AS schema_version,
            FALSE AS is_deleted

        FROM read_parquet(?)
        """,
        [
            args.batch_id,
            ingested_at,
            str(parquet_path),
        ],
    )

    loaded_rows = connection.execute(
        """
        SELECT COUNT(*)
        FROM raw.raw_customer
        WHERE migration_batch_id = ?
        """,
        [args.batch_id],
    ).fetchone()[0]

    connection.close()

    print(f"Batch ID: {args.batch_id}")
    print(f"Rows loaded: {loaded_rows}")
    print(f"DuckDB: {duckdb_path}")
    print("Target table: raw.raw_customer")


if __name__ == "__main__":
    main()