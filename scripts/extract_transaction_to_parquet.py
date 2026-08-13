import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv
from psycopg.rows import dict_row


LANDING_DIRECTORY = Path(
    "data/landing/payments/bank_transaction"
)


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch-id",
        default=str(uuid.uuid4()),
    )

    args = parser.parse_args()

    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    batch_directory = LANDING_DIRECTORY / args.batch_id

    if batch_directory.exists():
        raise RuntimeError(
            f"Batch directory already exists: {batch_directory}"
        )

    batch_directory.mkdir(parents=True)

    parquet_path = (
        batch_directory / "bank_transaction.parquet"
    )

    manifest_path = (
        batch_directory / "manifest.json"
    )

    extracted_at = datetime.now(timezone.utc)

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
                    updated_at
                FROM payments.bank_transaction
                ORDER BY transaction_id
                """
            )

            rows = cursor.fetchall()

    if not rows:
        raise RuntimeError(
            "No transaction records were extracted"
        )

    table = pa.Table.from_pylist(rows)

    pq.write_table(
        table,
        parquet_path,
    )

    manifest = {
        "batch_id": args.batch_id,
        "source_system": "neon_postgresql",
        "source_table": "payments.bank_transaction",
        "file_name": parquet_path.name,
        "file_format": "parquet",
        "row_count": len(rows),
        "min_source_key": rows[0]["transaction_id"],
        "max_source_key": rows[-1]["transaction_id"],
        "min_updated_at": min(
            row["updated_at"] for row in rows
        ).isoformat(),
        "max_updated_at": max(
            row["updated_at"] for row in rows
        ).isoformat(),
        "extracted_at": extracted_at.isoformat(),
        "sha256": calculate_sha256(parquet_path),
        "schema_version": "1.0",
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Batch ID: {args.batch_id}")
    print(f"Rows extracted: {len(rows)}")
    print(f"Parquet file: {parquet_path}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()