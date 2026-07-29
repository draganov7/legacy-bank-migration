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


if __name__ == "__main__":
    main()