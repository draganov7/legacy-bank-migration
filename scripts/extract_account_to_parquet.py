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


LANDING_DIRECTORY = Path("data/landing/core/account")


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

    parquet_path = batch_directory / "account.parquet"
    manifest_path = batch_directory / "manifest.json"

    extracted_at = datetime.now(timezone.utc)

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
                    updated_at
                FROM core.account
                ORDER BY account_id
                """
            )

            rows = cursor.fetchall()

    if not rows:
        raise RuntimeError("No account records were extracted")

    table = pa.Table.from_pylist(rows)

    pq.write_table(
        table,
        parquet_path,
    )

    manifest = {
        "batch_id": args.batch_id,
        "source_system": "neon_postgresql",
        "source_table": "core.account",
        "file_name": parquet_path.name,
        "file_format": "parquet",
        "row_count": len(rows),
        "min_source_key": rows[0]["account_id"],
        "max_source_key": rows[-1]["account_id"],
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