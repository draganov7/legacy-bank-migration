import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


QUARANTINE_DIRECTORY = Path("data/quarantine")
SUMMARY_PATH = Path("docs/data_quality/validation_summary.md")


def write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(
                json.dumps(
                    record,
                    default=str,
                    sort_keys=True,
                )
                + "\n"
            )


def quarantine_record(
    *,
    source_table: str,
    source_record_key: str,
    rule_id: str,
    severity: str,
    error_message: str,
    raw_payload: dict[str, Any],
    rejected_at: str,
) -> dict[str, Any]:
    return {
        "source_system": "neon_postgresql",
        "source_table": source_table,
        "source_record_key": source_record_key,
        "rule_id": rule_id,
        "severity": severity,
        "error_message": error_message,
        "raw_payload": raw_payload,
        "rejected_at": rejected_at,
        "resolution_status": "OPEN",
    }


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    rejected_at = datetime.now(timezone.utc).isoformat()

    rejected_customers: list[dict[str, Any]] = []
    rejected_transactions: list[dict[str, Any]] = []

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM core.customer
                WHERE date_of_birth > CURRENT_DATE
                ORDER BY customer_id
                """
            )

            for customer in cursor.fetchall():
                rejected_customers.append(
                    quarantine_record(
                        source_table="core.customer",
                        source_record_key=str(
                            customer["customer_id"]
                        ),
                        rule_id="CUSTOMER_DOB_NOT_FUTURE",
                        severity="HIGH",
                        error_message=(
                            "Customer date of birth is in the future."
                        ),
                        raw_payload=customer,
                        rejected_at=rejected_at,
                    )
                )

            cursor.execute(
                """
                SELECT *
                FROM core.customer
                WHERE email IS NOT NULL
                  AND email NOT LIKE '%_@_%._%'
                ORDER BY customer_id
                """
            )

            for customer in cursor.fetchall():
                rejected_customers.append(
                    quarantine_record(
                        source_table="core.customer",
                        source_record_key=str(
                            customer["customer_id"]
                        ),
                        rule_id="CUSTOMER_EMAIL_FORMAT",
                        severity="HIGH",
                        error_message=(
                            "Customer email does not match the "
                            "required format."
                        ),
                        raw_payload=customer,
                        rejected_at=rejected_at,
                    )
                )

            cursor.execute(
                """
                SELECT *
                FROM payments.bank_transaction
                WHERE currency_code NOT IN ('INR')
                ORDER BY transaction_id
                """
            )

            for transaction in cursor.fetchall():
                rejected_transactions.append(
                    quarantine_record(
                        source_table=(
                            "payments.bank_transaction"
                        ),
                        source_record_key=str(
                            transaction["transaction_id"]
                        ),
                        rule_id=(
                            "TRANSACTION_CURRENCY_REFERENCE"
                        ),
                        severity="HIGH",
                        error_message=(
                            "Transaction currency is not present "
                            "in the approved reference list."
                        ),
                        raw_payload=transaction,
                        rejected_at=rejected_at,
                    )
                )

            cursor.execute(
                """
                SELECT transaction.*
                FROM payments.bank_transaction AS transaction
                JOIN core.account AS account
                    ON transaction.source_account_id
                       = account.account_id
                WHERE account.status = 'CLOSED'
                  AND account.closed_date
                      < transaction.transaction_ts::date
                ORDER BY transaction.transaction_id
                """
            )

            for transaction in cursor.fetchall():
                rejected_transactions.append(
                    quarantine_record(
                        source_table=(
                            "payments.bank_transaction"
                        ),
                        source_record_key=str(
                            transaction["transaction_id"]
                        ),
                        rule_id="CLOSED_ACCOUNT_TRANSACTION",
                        severity="HIGH",
                        error_message=(
                            "Transaction occurred after the source "
                            "account was closed."
                        ),
                        raw_payload=transaction,
                        rejected_at=rejected_at,
                    )
                )

    QUARANTINE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )
    SUMMARY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    customer_path = (
        QUARANTINE_DIRECTORY
        / "rejected_customers.jsonl"
    )
    transaction_path = (
        QUARANTINE_DIRECTORY
        / "rejected_transactions.jsonl"
    )

    write_jsonl(customer_path, rejected_customers)
    write_jsonl(transaction_path, rejected_transactions)

    summary = f"""# Source Validation Summary

## Validation run

- Source system: Neon PostgreSQL
- Run timestamp: {rejected_at}
- Validation stage: pre-migration source assessment

## Results

| Source table | Rejected records |
|---|---:|
| core.customer | {len(rejected_customers)} |
| payments.bank_transaction | {len(rejected_transactions)} |
| **Total** | **{len(rejected_customers) + len(rejected_transactions)}** |

## Rules evaluated

| Rule ID | Severity | Expected records |
|---|---|---:|
| CUSTOMER_DOB_NOT_FUTURE | HIGH | 1 |
| CUSTOMER_EMAIL_FORMAT | HIGH | 1 |
| TRANSACTION_CURRENCY_REFERENCE | HIGH | 1 |
| CLOSED_ACCOUNT_TRANSACTION | HIGH | 1 |

## Quarantine behavior

Rejected records retain:

- source system
- source table
- source record key
- rule ID
- severity
- error message
- raw source payload
- rejection timestamp
- resolution status

The local JSON Lines files are ignored by Git because they contain
record-level source data. Only this summary is committed as portfolio
evidence.
"""

    SUMMARY_PATH.write_text(
        summary,
        encoding="utf-8",
    )

    print(
        f"Rejected customers: {len(rejected_customers)}"
    )
    print(
        "Rejected transactions: "
        f"{len(rejected_transactions)}"
    )
    print(
        "Total rejected records: "
        f"{len(rejected_customers) + len(rejected_transactions)}"
    )
    print(f"Validation summary: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()