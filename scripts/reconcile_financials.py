import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import psycopg
from dotenv import load_dotenv


REPORT_PATH = Path(
    "docs/reconciliation/financial_reconciliation.md"
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

    with psycopg.connect(source_database_url) as source:
        with source.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(amount), 0)
                FROM payments.bank_transaction
                """
            )

            (
                source_transaction_count,
                source_transaction_amount,
            ) = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(debit_total), 0),
                    COALESCE(SUM(credit_total), 0)
                FROM finance.daily_account_balance
                """
            )

            (
                source_balance_count,
                source_debit_total,
                source_credit_total,
            ) = cursor.fetchone()

    # ---------------------------------------------------------
    # DUCKDB METRICS
    # ---------------------------------------------------------

    con = duckdb.connect(duckdb_path)

    raw_transaction_count, raw_transaction_amount = con.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(amount), 0)
        FROM raw.raw_transaction
        """
    ).fetchone()

    raw_balance_count, raw_debits, raw_credits = con.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(debit_total), 0),
            COALESCE(SUM(credit_total), 0)
        FROM raw.raw_daily_account_balance
        """
    ).fetchone()

    core_transaction_count, core_transaction_amount = con.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(transaction_amount), 0)
        FROM core.fct_transaction
        """
    ).fetchone()

    core_balance_count, core_debits, core_credits = con.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(debit_total), 0),
            COALESCE(SUM(credit_total), 0)
        FROM core.fct_daily_balance
        """
    ).fetchone()

    rejected_transaction_count = con.execute(
        """
        SELECT COUNT(DISTINCT source_record_key)
        FROM quarantine.rejected_transaction
        """
    ).fetchone()[0]

    rejected_balance_count = con.execute(
        """
        SELECT COUNT(DISTINCT source_record_key)
        FROM quarantine.rejected_daily_balance
        """
    ).fetchone()[0]

    balance_equation_failures = con.execute(
        """
        SELECT COUNT(*)
        FROM core.fct_daily_balance
        WHERE opening_balance
              + credit_total
              - debit_total
              <> closing_balance
        """
    ).fetchone()[0]

    roll_forward_failures = con.execute(
        """
        WITH ordered AS (
            SELECT
                account_id,
                business_date,
                opening_balance,

                LAG(closing_balance) OVER (
                    PARTITION BY account_id
                    ORDER BY business_date
                ) AS previous_closing

            FROM core.fct_daily_balance
        )

        SELECT COUNT(*)
        FROM ordered
        WHERE previous_closing IS NOT NULL
          AND opening_balance <> previous_closing
        """
    ).fetchone()[0]

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
            reconciliation.financial_reconciliation (
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
        DELETE FROM reconciliation.financial_reconciliation
        """
    )

    checks = []

    def add_check(
        check_name: str,
        source_value,
        target_value,
    ) -> None:
        variance = source_value - target_value

        status = (
            "PASS"
            if variance == 0
            else "FAIL"
        )

        checks.append(
            (
                run_at,
                check_name,
                str(source_value),
                str(target_value),
                str(variance),
                status,
            )
        )

    # Source internal financial integrity
    add_check(
        "source_transaction_vs_debits",
        source_transaction_amount,
        source_debit_total,
    )

    add_check(
        "source_transaction_vs_credits",
        source_transaction_amount,
        source_credit_total,
    )

    # Source → raw migration
    add_check(
        "source_vs_raw_transaction_count",
        source_transaction_count,
        raw_transaction_count,
    )

    add_check(
        "source_vs_raw_transaction_amount",
        source_transaction_amount,
        raw_transaction_amount,
    )

    add_check(
        "source_vs_raw_balance_count",
        source_balance_count,
        raw_balance_count,
    )

    add_check(
        "source_vs_raw_debit_total",
        source_debit_total,
        raw_debits,
    )

    add_check(
        "source_vs_raw_credit_total",
        source_credit_total,
        raw_credits,
    )

    # Raw internal financial integrity
    add_check(
        "raw_transaction_vs_debits",
        raw_transaction_amount,
        raw_debits,
    )

    add_check(
        "raw_transaction_vs_credits",
        raw_transaction_amount,
        raw_credits,
    )

    # Accepted/rejected completeness
    add_check(
        "raw_balance_rows_vs_core_plus_rejected",
        raw_balance_count,
        core_balance_count + rejected_balance_count,
    )

    # Financial equations
    add_check(
        "core_balance_equation_failures",
        0,
        balance_equation_failures,
    )

    add_check(
        "core_roll_forward_failures",
        0,
        roll_forward_failures,
    )

    con.executemany(
        """
        INSERT INTO reconciliation.financial_reconciliation
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        checks,
    )

    failed_checks = sum(
        check[-1] == "FAIL"
        for check in checks
    )

    # This is informational, not automatically a failure.
    accepted_debit_variance = (
        core_debits - core_transaction_amount
    )

    accepted_credit_variance = (
        core_credits - core_transaction_amount
    )

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------

    check_rows = "\n".join(
        (
            f"| {row[1]} | {row[2]} | {row[3]} | "
            f"{row[4]} | {row[5]} |"
        )
        for row in checks
    )

    report = f"""# Financial Reconciliation Report

## Run

- Run timestamp: {run_at.isoformat()}

## Source totals

| Metric | Value |
|---|---:|
| Transaction rows | {source_transaction_count} |
| Transaction amount | {source_transaction_amount} |
| Balance rows | {source_balance_count} |
| Debit total | {source_debit_total} |
| Credit total | {source_credit_total} |

## Raw target totals

| Metric | Value |
|---|---:|
| Transaction rows | {raw_transaction_count} |
| Transaction amount | {raw_transaction_amount} |
| Balance rows | {raw_balance_count} |
| Debit total | {raw_debits} |
| Credit total | {raw_credits} |

## Accepted target totals

| Metric | Value |
|---|---:|
| Transaction rows | {core_transaction_count} |
| Transaction amount | {core_transaction_amount} |
| Balance rows | {core_balance_count} |
| Debit total | {core_debits} |
| Credit total | {core_credits} |

## Quarantine

| Metric | Value |
|---|---:|
| Rejected transaction records | {rejected_transaction_count} |
| Rejected balance records | {rejected_balance_count} |

## Critical checks

| Check | Expected | Actual | Variance | Status |
|---|---:|---:|---:|---|
{check_rows}

## Accepted cross-fact comparison

| Metric | Variance |
|---|---:|
| Core balance debits minus accepted transaction amount | {accepted_debit_variance} |
| Core balance credits minus accepted transaction amount | {accepted_credit_variance} |

The accepted transaction and balance totals are reported separately because
transactions rejected for referential-quality reasons may still contribute
to source daily balances for otherwise valid accounts.

This variance is therefore not automatically classified as a migration
failure. It must be explained through the rejected-record population.

## Summary

Failed critical checks: {failed_checks}
"""

    REPORT_PATH.write_text(
        report,
        encoding="utf-8",
    )

    con.close()

    print(f"Source transaction amount: {source_transaction_amount}")
    print(f"Source debit total: {source_debit_total}")
    print(f"Source credit total: {source_credit_total}")

    print(f"Raw transaction amount: {raw_transaction_amount}")
    print(f"Raw debit total: {raw_debits}")
    print(f"Raw credit total: {raw_credits}")

    print(f"Core transaction amount: {core_transaction_amount}")
    print(f"Core debit total: {core_debits}")
    print(f"Core credit total: {core_credits}")

    print(
        f"Accepted debit variance: {accepted_debit_variance}"
    )
    print(
        f"Accepted credit variance: {accepted_credit_variance}"
    )

    print(f"Failed critical checks: {failed_checks}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()