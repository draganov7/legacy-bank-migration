import os
from datetime import datetime, timezone

import duckdb
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    duckdb_path = os.getenv("DUCKDB_PATH")

    if not duckdb_path:
        raise RuntimeError("DUCKDB_PATH is not set")

    rejected_at = datetime.now(timezone.utc)

    con = duckdb.connect(duckdb_path)

    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    con.execute("CREATE SCHEMA IF NOT EXISTS quarantine")

    con.execute(
        """
        CREATE OR REPLACE TABLE staging.stg_account AS

        SELECT
            account_id,
            TRIM(account_number) AS account_number,
            customer_id,
            branch_id,
            UPPER(account_type) AS account_type,
            UPPER(currency_code) AS currency_code,
            opened_date,
            closed_date,
            UPPER(status) AS account_status,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM raw.raw_account AS account

        WHERE EXISTS (
            SELECT 1
            FROM core.dim_customer AS customer
            WHERE customer.customer_id = account.customer_id
        )

          AND currency_code = 'INR'

          AND (
              closed_date IS NULL
              OR closed_date >= opened_date
          )

          AND account_type IN (
              'SAVINGS',
              'CURRENT',
              'LOAN',
              'CREDIT_CARD'
          )

          AND status IN (
              'ACTIVE',
              'DORMANT',
              'FROZEN',
              'CLOSED'
          )
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE quarantine.rejected_account AS

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'ACCOUNT_CUSTOMER_REFERENCE' AS rule_id,
            'CRITICAL' AS severity,

            'Account customer_id does not resolve to a valid customer.'
                AS error_message,

            to_json(
                struct_pack(
                    account_id := account_id,
                    account_number := account_number,
                    customer_id := customer_id,
                    branch_id := branch_id,
                    account_type := account_type,
                    currency_code := currency_code,
                    opened_date := opened_date,
                    closed_date := closed_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_account AS account

        WHERE NOT EXISTS (
            SELECT 1
            FROM core.dim_customer AS customer
            WHERE customer.customer_id = account.customer_id
        )

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'ACCOUNT_CURRENCY_REFERENCE' AS rule_id,
            'HIGH' AS severity,

            'Account currency is not in the approved currency list.'
                AS error_message,

            to_json(
                struct_pack(
                    account_id := account_id,
                    account_number := account_number,
                    customer_id := customer_id,
                    branch_id := branch_id,
                    account_type := account_type,
                    currency_code := currency_code,
                    opened_date := opened_date,
                    closed_date := closed_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_account
        WHERE currency_code <> 'INR'

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'ACCOUNT_DATE_RANGE' AS rule_id,
            'HIGH' AS severity,

            'Account closed_date is earlier than opened_date.'
                AS error_message,

            to_json(
                struct_pack(
                    account_id := account_id,
                    account_number := account_number,
                    customer_id := customer_id,
                    branch_id := branch_id,
                    account_type := account_type,
                    currency_code := currency_code,
                    opened_date := opened_date,
                    closed_date := closed_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_account
        WHERE closed_date IS NOT NULL
          AND closed_date < opened_date

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'ACCOUNT_TYPE_REFERENCE' AS rule_id,
            'HIGH' AS severity,

            'Account type is not approved.'
                AS error_message,

            to_json(
                struct_pack(
                    account_id := account_id,
                    account_number := account_number,
                    customer_id := customer_id,
                    branch_id := branch_id,
                    account_type := account_type,
                    currency_code := currency_code,
                    opened_date := opened_date,
                    closed_date := closed_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_account
        WHERE account_type NOT IN (
            'SAVINGS',
            'CURRENT',
            'LOAN',
            'CREDIT_CARD'
        )

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'ACCOUNT_STATUS_REFERENCE' AS rule_id,
            'HIGH' AS severity,

            'Account status is not approved.'
                AS error_message,

            to_json(
                struct_pack(
                    account_id := account_id,
                    account_number := account_number,
                    customer_id := customer_id,
                    branch_id := branch_id,
                    account_type := account_type,
                    currency_code := currency_code,
                    opened_date := opened_date,
                    closed_date := closed_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_account
        WHERE status NOT IN (
            'ACTIVE',
            'DORMANT',
            'FROZEN',
            'CLOSED'
        )
        """,
        [
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
        ],
    )

    raw_count = con.execute(
        "SELECT COUNT(*) FROM raw.raw_account"
    ).fetchone()[0]

    valid_count = con.execute(
        "SELECT COUNT(*) FROM staging.stg_account"
    ).fetchone()[0]

    rejected_records = con.execute(
        """
        SELECT COUNT(DISTINCT source_record_key)
        FROM quarantine.rejected_account
        """
    ).fetchone()[0]

    rule_failures = con.execute(
        """
        SELECT COUNT(*)
        FROM quarantine.rejected_account
        """
    ).fetchone()[0]

    con.close()

    print(f"Raw accounts: {raw_count}")
    print(f"Valid accounts: {valid_count}")
    print(f"Rejected account records: {rejected_records}")
    print(f"Rule failures: {rule_failures}")


if __name__ == "__main__":
    main()