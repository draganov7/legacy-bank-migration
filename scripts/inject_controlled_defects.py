import os
from datetime import date, timedelta

import psycopg
from dotenv import load_dotenv


DEFECTS = [
    {
        "defect_id": "DEF-CUST-001",
        "source_table": "core.customer",
        "source_record_key": "1",
        "rule_id": "CUSTOMER_DOB_NOT_FUTURE",
        "defect_description": "Customer date of birth is in the future.",
        "expected_handling": "QUARANTINE",
    },
    {
        "defect_id": "DEF-CUST-002",
        "source_table": "core.customer",
        "source_record_key": "2",
        "rule_id": "CUSTOMER_EMAIL_FORMAT",
        "defect_description": "Customer email has an invalid format.",
        "expected_handling": "QUARANTINE",
    },
    {
        "defect_id": "DEF-TRX-001",
        "source_table": "payments.bank_transaction",
        "source_record_key": "1",
        "rule_id": "TRANSACTION_CURRENCY_REFERENCE",
        "defect_description": "Transaction uses unsupported currency code ZZZ.",
        "expected_handling": "QUARANTINE",
    },
    {
        "defect_id": "DEF-TRX-002",
        "source_table": "payments.bank_transaction",
        "source_record_key": "2",
        "rule_id": "CLOSED_ACCOUNT_TRANSACTION",
        "defect_description": (
            "Transaction source account is marked CLOSED before "
            "the transaction timestamp."
        ),
        "expected_handling": "QUARANTINE",
    },
]


def record_defect(
    cursor: psycopg.Cursor,
    defect: dict[str, str],
) -> None:
    cursor.execute(
        """
        INSERT INTO control.defect_manifest (
            defect_id,
            source_table,
            source_record_key,
            rule_id,
            defect_description,
            expected_handling
        )
        VALUES (
            %(defect_id)s,
            %(source_table)s,
            %(source_record_key)s,
            %(rule_id)s,
            %(defect_description)s,
            %(expected_handling)s
        )
        ON CONFLICT (defect_id) DO NOTHING
        """,
        defect,
    )


def main() -> None:
    load_dotenv()

    database_url = os.getenv("SOURCE_DATABASE_URL")

    if not database_url:
        raise RuntimeError("SOURCE_DATABASE_URL is not set")

    future_date = date.today() + timedelta(days=365)

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            # Defect 1: future date of birth
            cursor.execute(
                """
                UPDATE core.customer
                SET
                    date_of_birth = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE customer_id = 1
                """,
                (future_date,),
            )

            # Defect 2: malformed email
            cursor.execute(
                """
                UPDATE core.customer
                SET
                    email = 'invalid-email',
                    updated_at = CURRENT_TIMESTAMP
                WHERE customer_id = 2
                """
            )

            # Defect 3: unsupported currency
            cursor.execute(
                """
                UPDATE payments.bank_transaction
                SET
                    currency_code = 'ZZZ',
                    updated_at = CURRENT_TIMESTAMP
                WHERE transaction_id = 1
                """
            )

            # Defect 4: close the source account before transaction 2
            cursor.execute(
                """
                SELECT
                    source_account_id,
                    transaction_ts::date
                FROM payments.bank_transaction
                WHERE transaction_id = 2
                """
            )

            row = cursor.fetchone()

            if row is None:
                raise RuntimeError("Transaction 2 does not exist")

            account_id, transaction_date = row
            closed_date = transaction_date - timedelta(days=1)

            cursor.execute(
                """
                UPDATE core.account
                SET
                    status = 'CLOSED',
                    closed_date = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = %s
                """,
                (closed_date, account_id),
            )

            for defect in DEFECTS:
                record_defect(cursor, defect)

        connection.commit()

    print(f"Injected controlled defects: {len(DEFECTS)}")


if __name__ == "__main__":
    main()