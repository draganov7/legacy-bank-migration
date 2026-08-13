import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import psycopg
from dotenv import load_dotenv


REPORT_PATH = Path(
    "docs/reconciliation/transaction_reconciliation.md"
)


def main() -> None:
    load_dotenv()

    source_database_url = os.getenv("SOURCE_DATABASE_URL")
    duckdb_path = os.getenv("DUCKDB_PATH")

    if not source_database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    if not duckdb_path:
        raise RuntimeError("DUCKDB_PATH is not set")

    run_at = datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # SOURCE METRICS
    # ---------------------------------------------------------

    with psycopg.connect(source_database_url) as source_connection:
        with source_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(amount), 0),
                    COUNT(*) FILTER (
                        WHERE aml_flag = TRUE
                    )
                FROM payments.bank_transaction
                """
            )

            (
                source_count,
                source_amount,
                source_aml_count,
            ) = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    transaction_type,
                    COUNT(*),
                    COALESCE(SUM(amount), 0)
                FROM payments.bank_transaction
                GROUP BY transaction_type
                ORDER BY transaction_type
                """
            )

            source_by_type = {
                row[0]: {
                    "count": row[1],
                    "amount": row[2],
                }
                for row in cursor.fetchall()
            }

    # ---------------------------------------------------------
    # TARGET METRICS
    # ---------------------------------------------------------

    con = duckdb.connect(duckdb_path)

    raw_count, raw_amount, raw_aml_count = con.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(amount), 0),
            COUNT(*) FILTER (
                WHERE aml_flag = TRUE
            )
        FROM raw.raw_transaction
        """
    ).fetchone()

    staging_count, staging_amount = con.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(transaction_amount), 0)
        FROM staging.stg_transaction
        """
    ).fetchone()

    core_count, core_amount, core_aml_count = con.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(transaction_amount), 0),
            COUNT(*) FILTER (
                WHERE is_aml_flagged = TRUE
            )
        FROM core.fct_transaction
        """
    ).fetchone()

    rejected_record_count = con.execute(
        """
        SELECT COUNT(DISTINCT source_record_key)
        FROM quarantine.rejected_transaction
        """
    ).fetchone()[0]

    rejected_amount = con.execute(
        """
        SELECT COALESCE(
            SUM(amount),
            0
        )
        FROM raw.raw_transaction
        WHERE CAST(transaction_id AS VARCHAR) IN (
            SELECT DISTINCT source_record_key
            FROM quarantine.rejected_transaction
        )
        """
    ).fetchone()[0]

    core_by_type_rows = con.execute(
        """
        SELECT
            transaction_type,
            COUNT(*),
            COALESCE(SUM(transaction_amount), 0)
        FROM core.fct_transaction
        GROUP BY transaction_type
        ORDER BY transaction_type
        """
    ).fetchall()

    core_by_type = {
        row[0]: {
            "count": row[1],
            "amount": row[2],
        }
        for row in core_by_type_rows
    }

    # ---------------------------------------------------------
    # RECONCILIATION TABLE
    # ---------------------------------------------------------

    con.execute(
        """
        CREATE SCHEMA IF NOT EXISTS reconciliation
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS
            reconciliation.transaction_reconciliation (
                run_at TIMESTAMPTZ,
                check_name VARCHAR,
                source_value VARCHAR,
                target_value VARCHAR,
                variance VARCHAR,
                status VARCHAR
            )
        """
    )

    con.execute(
        """
        DELETE FROM reconciliation.transaction_reconciliation
        """
    )

    checks = []

    def add_check(
        name: str,
        source_value,
        target_value,
    ) -> None:
        variance = source_value - target_value
        status = "PASS" if variance == 0 else "FAIL"

        checks.append(
            (
                run_at,
                name,
                str(source_value),
                str(target_value),
                str(variance),
                status,
            )
        )

    add_check(
        "source_vs_raw_row_count",
        source_count,
        raw_count,
    )

    add_check(
        "raw_vs_valid_plus_rejected",
        raw_count,
        staging_count + rejected_record_count,
    )

    add_check(
        "staging_vs_core_row_count",
        staging_count,
        core_count,
    )

    add_check(
        "source_vs_raw_amount",
        source_amount,
        raw_amount,
    )

    add_check(
        "raw_vs_core_plus_rejected_amount",
        raw_amount,
        core_amount + rejected_amount,
    )

    add_check(
        "staging_vs_core_amount",
        staging_amount,
        core_amount,
    )

    add_check(
        "source_vs_raw_aml_count",
        source_aml_count,
        raw_aml_count,
    )

    con.executemany(
        """
        INSERT INTO reconciliation.transaction_reconciliation
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        checks,
    )

    failed_checks = sum(
        1 for check in checks if check[-1] == "FAIL"
    )

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------

    type_rows = []

    for transaction_type in sorted(source_by_type):
        source_metrics = source_by_type[transaction_type]

        target_metrics = core_by_type.get(
            transaction_type,
            {
                "count": 0,
                "amount": 0,
            },
        )

        type_rows.append(
            "| "
            f"{transaction_type} | "
            f"{source_metrics['count']} | "
            f"{source_metrics['amount']} | "
            f"{target_metrics['count']} | "
            f"{target_metrics['amount']} |"
        )

    report = f"""# Transaction Reconciliation Report

## Run

- Run timestamp: {run_at.isoformat()}

## Row counts

| Metric | Value |
|---|---:|
| Source rows | {source_count} |
| Raw rows | {raw_count} |
| Valid staging rows | {staging_count} |
| Rejected distinct records | {rejected_record_count} |
| Core rows | {core_count} |

## Amount reconciliation

| Metric | Amount |
|---|---:|
| Source amount | {source_amount} |
| Raw amount | {raw_amount} |
| Valid staging amount | {staging_amount} |
| Rejected amount | {rejected_amount} |
| Core amount | {core_amount} |

## AML reconciliation

| Metric | Count |
|---|---:|
| Source AML flagged | {source_aml_count} |
| Raw AML flagged | {raw_aml_count} |
| Core AML flagged | {core_aml_count} |

## Transaction type comparison

| Type | Source count | Source amount | Core count | Core amount |
|---|---:|---:|---:|---:|
{chr(10).join(type_rows)}

## Check results

| Check | Source | Target | Variance | Status |
|---|---:|---:|---:|---|
{chr(10).join(
    f"| {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |"
    for row in checks
)}

## Summary

Failed reconciliation checks: {failed_checks}
"""

    REPORT_PATH.write_text(
        report,
        encoding="utf-8",
    )

    con.close()

    print(f"Source rows: {source_count}")
    print(f"Raw rows: {raw_count}")
    print(f"Valid rows: {staging_count}")
    print(f"Rejected records: {rejected_record_count}")
    print(f"Core rows: {core_count}")
    print(f"Failed checks: {failed_checks}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()