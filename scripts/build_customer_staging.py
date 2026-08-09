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
        CREATE OR REPLACE TABLE staging.stg_customer AS
        SELECT
            customer_id,
            TRIM(customer_number) AS customer_number,
            TRIM(full_name) AS customer_name,
            date_of_birth,
            LOWER(TRIM(email)) AS email_normalised,
            phone,
            country_code,
            kyc_status,
            customer_status,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM raw.raw_customer

        WHERE date_of_birth <= CURRENT_DATE
          AND (
              email IS NULL
              OR email LIKE '%_@_%._%'
          )
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE quarantine.rejected_customer AS

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'CUSTOMER_DOB_NOT_FUTURE' AS rule_id,
            'HIGH' AS severity,
            'Customer date of birth is in the future.' AS error_message,

            to_json(
                struct_pack(
                    customer_id := customer_id,
                    customer_number := customer_number,
                    full_name := full_name,
                    date_of_birth := date_of_birth,
                    email := email,
                    phone := phone,
                    country_code := country_code,
                    kyc_status := kyc_status,
                    customer_status := customer_status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_customer
        WHERE date_of_birth > CURRENT_DATE

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'CUSTOMER_EMAIL_FORMAT' AS rule_id,
            'HIGH' AS severity,
            'Customer email format is invalid.' AS error_message,

            to_json(
                struct_pack(
                    customer_id := customer_id,
                    customer_number := customer_number,
                    full_name := full_name,
                    date_of_birth := date_of_birth,
                    email := email,
                    phone := phone,
                    country_code := country_code,
                    kyc_status := kyc_status,
                    customer_status := customer_status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_customer
        WHERE email IS NOT NULL
          AND email NOT LIKE '%_@_%._%'
        """,
        [rejected_at, rejected_at],
    )

    raw_count = con.execute(
        "SELECT COUNT(*) FROM raw.raw_customer"
    ).fetchone()[0]

    valid_count = con.execute(
        "SELECT COUNT(*) FROM staging.stg_customer"
    ).fetchone()[0]

    rejected_count = con.execute(
        "SELECT COUNT(*) FROM quarantine.rejected_customer"
    ).fetchone()[0]

    con.close()

    print(f"Raw customers: {raw_count}")
    print(f"Valid customers: {valid_count}")
    print(f"Rejected customers: {rejected_count}")


if __name__ == "__main__":
    main()