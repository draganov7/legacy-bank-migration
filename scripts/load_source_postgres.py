from asyncio import coroutines
import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


DATA_DIRECTORY = Path("data/generated")


def read_csv(file_name: str) -> list[dict[str, str | bool | None]]:
    path = DATA_DIRECTORY / file_name

    if not path.exists():
        raise RuntimeError(
            f"{path} does not exist. Run generate_source_data.py first."
        )

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        for key, value in row.items():
            if value == "":
                row[key] = None
        if "aml_flag" in row and row["aml_flag"] is not None:
            row["aml_flag"] = row["aml_flag"] == "True"

    return rows


def load_branches(
    cursor: psycopg.Cursor,
    rows: list[dict[str, str | None]],
) -> None:
    cursor.executemany(
        """
        INSERT INTO core.branch (
            branch_id,
            branch_code,
            branch_name,
            city,
            state,
            operating_region,
            opened_date,
            status,
            created_at,
            updated_at
        )
        VALUES (
            %(branch_id)s,
            %(branch_code)s,
            %(branch_name)s,
            %(city)s,
            %(state)s,
            %(operating_region)s,
            %(opened_date)s,
            %(status)s,
            %(created_at)s,
            %(updated_at)s
        )
        """,
        rows,
    )


def load_customers(
    cursor: psycopg.Cursor,
    rows: list[dict[str, str | None]],
) -> None:
    cursor.executemany(
        """
        INSERT INTO core.customer (
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
            updated_at
        )
        VALUES (
            %(customer_id)s,
            %(customer_number)s,
            %(full_name)s,
            %(date_of_birth)s,
            %(email)s,
            %(phone)s,
            %(address_line_1)s,
            %(address_line_2)s,
            %(city)s,
            %(state)s,
            %(postal_code)s,
            %(country_code)s,
            %(kyc_status)s,
            %(customer_status)s,
            %(created_at)s,
            %(updated_at)s
        )
        """,
        rows,
    )


def load_accounts(
    cursor: psycopg.Cursor,
    rows: list[dict[str, str | None]],
) -> None:
    cursor.executemany(
        """
        INSERT INTO core.account (
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
        )
        VALUES (
            %(account_id)s,
            %(account_number)s,
            %(customer_id)s,
            %(branch_id)s,
            %(account_type)s,
            %(currency_code)s,
            %(opened_date)s,
            %(closed_date)s,
            %(status)s,
            %(created_at)s,
            %(updated_at)s
        )
        """,
        rows,
    )


def load_transactions(
    cursor: psycopg.Cursor,
    rows: list[dict[str, str | None]],
) -> None:
    cursor.executemany(
        """
        INSERT INTO payments.bank_transaction (
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
        )
        VALUES (
            %(transaction_id)s,
            %(source_account_id)s,
            %(destination_account_id)s,
            %(transaction_ts)s,
            %(transaction_type)s,
            %(amount)s,
            %(currency_code)s,
            %(payment_channel)s,
            %(aml_flag)s,
            %(created_at)s,
            %(updated_at)s
        )
        """,
        rows,
    )


def load_daily_balances(
    cursor: psycopg.Cursor,
    rows: list[dict[str, str | bool | None]],
) -> None:
    cursor.executemany(
        """
        INSERT INTO finance.daily_account_balance (
            account_id,
            business_date,
            opening_balance,
            debit_total,
            credit_total,
            closing_balance,
            created_at,
            updated_at
        )
        VALUES (
            %(account_id)s,
            %(business_date)s,
            %(opening_balance)s,
            %(debit_total)s,
            %(credit_total)s,
            %(closing_balance)s,
            %(created_at)s,
            %(updated_at)s
        )
        """,
        rows,
    )


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    branches = read_csv("branches.csv")
    customers = read_csv("customers.csv")
    accounts = read_csv("accounts.csv")
    transactions = read_csv("transactions.csv")
    daily_balaces = read_csv("daily_balances.csv")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE TABLE
                    finance.daily_account_balance,
                    payments.bank_transaction,
                    core.account,
                    core.customer,
                    core.branch
                RESTART IDENTITY CASCADE
                """
            )

            load_branches(cursor, branches)
            load_customers(cursor, customers)
            load_accounts(cursor, accounts)
            load_transactions(cursor, transactions)
            load_daily_balances(cursor, daily_balaces)

        connection.commit()

    print(f"Loaded branches: {len(branches)}")
    print(f"Loaded customers: {len(customers)}")
    print(f"Loaded accounts: {len(accounts)}")
    print(f"Loaded transactions: {len(transactions)}")
    print(f"Loaded daily balances: {len(daily_balaces)}")
    print("Source master data loaded successfully")


if __name__ == "__main__":
    main()