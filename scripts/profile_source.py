import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


OUTPUT_PATH = Path("docs/source_assessment/source_profile.md")


def fetch_value(cursor: psycopg.Cursor, query: str):
    cursor.execute(query)
    return cursor.fetchone()[0]


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            branch_count = fetch_value(
                cursor,
                "SELECT COUNT(*) FROM core.branch",
            )
            customer_count = fetch_value(
                cursor,
                "SELECT COUNT(*) FROM core.customer",
            )
            account_count = fetch_value(
                cursor,
                "SELECT COUNT(*) FROM core.account",
            )
            transaction_count = fetch_value(
                cursor,
                "SELECT COUNT(*) FROM payments.bank_transaction",
            )
            balance_count = fetch_value(
                cursor,
                "SELECT COUNT(*) FROM finance.daily_account_balance",
            )

            duplicate_customers = fetch_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT customer_id
                    FROM core.customer
                    GROUP BY customer_id
                    HAVING COUNT(*) > 1
                ) AS duplicates
                """,
            )

            duplicate_accounts = fetch_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT account_id
                    FROM core.account
                    GROUP BY account_id
                    HAVING COUNT(*) > 1
                ) AS duplicates
                """,
            )

            duplicate_transactions = fetch_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT transaction_id
                    FROM payments.bank_transaction
                    GROUP BY transaction_id
                    HAVING COUNT(*) > 1
                ) AS duplicates
                """,
            )

            orphan_accounts = fetch_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM core.account AS account
                LEFT JOIN core.customer AS customer
                    ON account.customer_id = customer.customer_id
                WHERE customer.customer_id IS NULL
                """,
            )

            orphan_transaction_accounts = fetch_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM payments.bank_transaction AS transaction
                LEFT JOIN core.account AS source_account
                    ON transaction.source_account_id =
                       source_account.account_id
                LEFT JOIN core.account AS destination_account
                    ON transaction.destination_account_id =
                       destination_account.account_id
                WHERE source_account.account_id IS NULL
                   OR destination_account.account_id IS NULL
                """,
            )

            cursor.execute(
                """
                SELECT
                    MIN(transaction_ts),
                    MAX(transaction_ts),
                    SUM(amount)
                FROM payments.bank_transaction
                """
            )
            min_transaction_ts, max_transaction_ts, transaction_total = (
                cursor.fetchone()
            )

            balance_equation_failures = fetch_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM finance.daily_account_balance
                WHERE opening_balance
                      + credit_total
                      - debit_total
                      <> closing_balance
                """,
            )

            roll_forward_failures = fetch_value(
                cursor,
                """
                WITH ordered_balances AS (
                    SELECT
                        account_id,
                        business_date,
                        opening_balance,
                        LAG(closing_balance) OVER (
                            PARTITION BY account_id
                            ORDER BY business_date
                        ) AS previous_closing_balance
                    FROM finance.daily_account_balance
                )
                SELECT COUNT(*)
                FROM ordered_balances
                WHERE previous_closing_balance IS NOT NULL
                  AND opening_balance <> previous_closing_balance
                """,
            )

            cursor.execute(
                """
                SELECT
                    SUM(debit_total),
                    SUM(credit_total)
                FROM finance.daily_account_balance
                """
            )
            debit_total, credit_total = cursor.fetchone()

    report = f"""# Minimal Source Profiling Report

## Row counts

| Table | Rows |
|---|---:|
| core.branch | {branch_count} |
| core.customer | {customer_count} |
| core.account | {account_count} |
| payments.bank_transaction | {transaction_count} |
| finance.daily_account_balance | {balance_count} |

## Key and relationship checks

| Check | Failures |
|---|---:|
| Duplicate customer IDs | {duplicate_customers} |
| Duplicate account IDs | {duplicate_accounts} |
| Duplicate transaction IDs | {duplicate_transactions} |
| Accounts without customers | {orphan_accounts} |
| Transactions with missing accounts | {orphan_transaction_accounts} |

## Transaction profile

| Metric | Value |
|---|---|
| Earliest transaction | {min_transaction_ts} |
| Latest transaction | {max_transaction_ts} |
| Total transaction amount | {transaction_total} |

## Financial checks

| Check | Result |
|---|---:|
| Balance equation failures | {balance_equation_failures} |
| Roll-forward failures | {roll_forward_failures} |
| Total transaction amount | {transaction_total} |
| Total balance debits | {debit_total} |
| Total balance credits | {credit_total} |

## Conclusion

This report represents the clean source baseline before controlled defects
are introduced.
"""

    OUTPUT_PATH.write_text(report, encoding="utf-8")

    print(f"Profile written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()