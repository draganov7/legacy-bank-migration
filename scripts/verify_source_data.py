from duckdb import cursor
import os

import psycopg
from dotenv import load_dotenv


EXPECTED_COUNTS = {
    "core.branch": 5,
    "core.customer": 50,
    "core.account": 75,
    "payments.bank_transaction": 500,
}


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            actual_counts = {}

            for table_name in EXPECTED_COUNTS:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                actual_counts[table_name] = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.account AS account
                LEFT JOIN core.customer AS customer
                    ON account.customer_id = customer.customer_id
                WHERE customer.customer_id IS NULL
                """
            )
            orphan_customers = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.account AS account
                LEFT JOIN core.branch AS branch
                    ON account.branch_id = branch.branch_id
                WHERE branch.branch_id IS NULL
                """
            )
            orphan_branches = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM payments.bank_transaction AS transaction
                LEFT JOIN core.account AS account
                    ON transaction.source_account_id = account.account_id
                WHERE account.account_id IS NULL
                """
            )
            missing_source_accounts = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM payments.bank_transaction AS transaction
                LEFT JOIN core.account AS account
                    ON transaction.destination_account_id = account.account_id
                WHERE account.account_id IS NULL
                """
            )
            missing_destination_accounts = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM payments.bank_transaction
                WHERE source_account_id = destination_account_id
                """
            )
            same_account_transactions = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM payments.bank_transaction
                WHERE amount <= 0
                """
            )
            invalid_amounts = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    SUM(amount),
                    COUNT(*) FILTER (WHERE aml_flag = TRUE)
                FROM payments.bank_transaction
                """
            )
            total_amount, aml_transaction_count = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM finance.daily_account_balance
                """
            )
            daily_balance_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM finance.daily_account_balance
                WHERE opening_balance + credit_total - debit_total <> closing_balance
                """
            )
            balance_equation_failures = cursor.fetchone()[0]

            cursor.execute(
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
                """
            )
            roll_forward_failures = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payments.bank_transaction
                """
            )
            transaction_total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(debit_total), 0),
                    COALESCE(SUM(credit_total), 0)
                FROM finance.daily_account_balance
                """
            )
            balance_debit_total, balance_credit_total = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM finance.daily_account_balance AS balance
                LEFT JOIN core.account AS account
                    ON balance.account_id = account.account_id
                WHERE account.account_id IS NULL
                """
            )
            orphan_balance_accounts = cursor.fetchone()[0]

    for table_name, expected_count in EXPECTED_COUNTS.items():
        actual_count = actual_counts[table_name]

        if actual_count != expected_count:
            raise RuntimeError(
                f"{table_name}: expected {expected_count}, "
                f"found {actual_count}"
            )

        print(f"{table_name}: {actual_count}")

    if orphan_customers != 0:
        raise RuntimeError(
            f"Accounts with missing customers: {orphan_customers}"
        )

    if orphan_branches != 0:
        raise RuntimeError(
            f"Accounts with missing branches: {orphan_branches}"
        )

    print("Accounts with missing customers: 0")
    print("Accounts with missing branches: 0")
    print("Source master data verified successfully")

    if missing_source_accounts != 0:
        raise RuntimeError(
            f"Transactions with missing source accounts: "
            f"{missing_source_accounts}"
        )

    if missing_destination_accounts != 0:
        raise RuntimeError(
            f"Transactions with missing destination accounts: "
            f"{missing_destination_accounts}"
        )

    if same_account_transactions != 0:
        raise RuntimeError(
            f"Transactions with identical accounts: "
            f"{same_account_transactions}"
        )

    if invalid_amounts != 0:
        raise RuntimeError(
            f"Transactions with invalid amounts: {invalid_amounts}"
        )

    print("Transactions with missing source accounts: 0")
    print("Transactions with missing destination accounts: 0")
    print("Transactions with identical accounts: 0")
    print("Transactions with invalid amounts: 0")
    print(f"Total transaction amount: ₹{total_amount}")
    print(f"AML-flagged transactions: {aml_transaction_count}")

    if daily_balance_count == 0:
        raise RuntimeError("No daily balance rows were loaded")

    if balance_equation_failures != 0:
        raise RuntimeError(
            f"Balance equation failures: {balance_equation_failures}"
        )

    if roll_forward_failures != 0:
        raise RuntimeError(
            f"Roll-forward failures: {roll_forward_failures}"
        )

    if orphan_balance_accounts != 0:
        raise RuntimeError(
            f"Balance rows with missing accounts: "
            f"{orphan_balance_accounts}"
        )

    if transaction_total != balance_debit_total:
        raise RuntimeError(
            "Transaction total does not match balance debit total: "
            f"{transaction_total} != {balance_debit_total}"
        )

    if transaction_total != balance_credit_total:
        raise RuntimeError(
            "Transaction total does not match balance credit total: "
            f"{transaction_total} != {balance_credit_total}"
        )

    print(f"finance.daily_account_balance: {daily_balance_count}")
    print("Balance equation failures: 0")
    print("Roll-forward failures: 0")
    print("Balance rows with missing accounts: 0")
    print(f"Transaction total: ₹{transaction_total}")
    print(f"Balance debit total: ₹{balance_debit_total}")
    print(f"Balance credit total: ₹{balance_credit_total}")


if __name__ == "__main__":
    main()