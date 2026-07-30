import os

import psycopg
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM control.defect_manifest
                """
            )
            manifest_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.customer
                WHERE date_of_birth > CURRENT_DATE
                """
            )
            future_dob_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.customer
                WHERE email IS NOT NULL
                  AND email NOT LIKE '%_@_%._%'
                """
            )
            invalid_email_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM payments.bank_transaction
                WHERE currency_code = 'ZZZ'
                """
            )
            invalid_currency_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM payments.bank_transaction AS transaction
                JOIN core.account AS account
                    ON transaction.source_account_id = account.account_id
                WHERE account.status = 'CLOSED'
                  AND account.closed_date < transaction.transaction_ts::date
                """
            )
            closed_account_transaction_count = cursor.fetchone()[0]

    if manifest_count != 4:
        raise RuntimeError(
            f"Expected 4 manifest records, found {manifest_count}"
        )

    if future_dob_count < 1:
        raise RuntimeError("Future DOB defect was not found")

    if invalid_email_count < 1:
        raise RuntimeError("Invalid email defect was not found")

    if invalid_currency_count < 1:
        raise RuntimeError("Invalid currency defect was not found")

    if closed_account_transaction_count < 1:
        raise RuntimeError(
            "Closed-account transaction defect was not found"
        )

    print(f"Defect manifest records: {manifest_count}")
    print(f"Future DOB records: {future_dob_count}")
    print(f"Invalid email records: {invalid_email_count}")
    print(f"Unsupported currency records: {invalid_currency_count}")
    print(
        "Transactions after account closure: "
        f"{closed_account_transaction_count}"
    )
    print("Controlled defects verified successfully")


if __name__ == "__main__":
    main()