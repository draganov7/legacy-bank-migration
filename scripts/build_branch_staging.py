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

    con.execute(
        """
        CREATE SCHEMA IF NOT EXISTS staging
        """
    )

    con.execute(
        """
        CREATE SCHEMA IF NOT EXISTS quarantine
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE staging.stg_branch AS

        SELECT
            branch_id,
            TRIM(branch_code) AS branch_code,
            TRIM(branch_name) AS branch_name,
            TRIM(city) AS city,
            TRIM(state) AS state,
            UPPER(TRIM(operating_region))
                AS operating_region,
            opened_date,
            UPPER(status) AS branch_status,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM raw.raw_branch

        WHERE branch_id IS NOT NULL

          AND branch_code IS NOT NULL
          AND TRIM(branch_code) <> ''

          AND branch_name IS NOT NULL
          AND TRIM(branch_name) <> ''

          AND opened_date IS NOT NULL

          AND status IN (
              'ACTIVE',
              'INACTIVE',
              'CLOSED'
          )
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE quarantine.rejected_branch AS

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BRANCH_CODE_REQUIRED'
                AS rule_id,

            'HIGH'
                AS severity,

            'Branch code is missing or blank.'
                AS error_message,

            to_json(
                struct_pack(
                    branch_id := branch_id,
                    branch_code := branch_code,
                    branch_name := branch_name,
                    city := city,
                    state := state,
                    operating_region := operating_region,
                    opened_date := opened_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ
                AS rejected_at,

            'OPEN'
                AS resolution_status

        FROM raw.raw_branch

        WHERE branch_code IS NULL
           OR TRIM(branch_code) = ''

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BRANCH_NAME_REQUIRED'
                AS rule_id,

            'HIGH'
                AS severity,

            'Branch name is missing or blank.'
                AS error_message,

            to_json(
                struct_pack(
                    branch_id := branch_id,
                    branch_code := branch_code,
                    branch_name := branch_name,
                    city := city,
                    state := state,
                    operating_region := operating_region,
                    opened_date := opened_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ
                AS rejected_at,

            'OPEN'
                AS resolution_status

        FROM raw.raw_branch

        WHERE branch_name IS NULL
           OR TRIM(branch_name) = ''

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BRANCH_OPENED_DATE_REQUIRED'
                AS rule_id,

            'HIGH'
                AS severity,

            'Branch opened_date is missing.'
                AS error_message,

            to_json(
                struct_pack(
                    branch_id := branch_id,
                    branch_code := branch_code,
                    branch_name := branch_name,
                    city := city,
                    state := state,
                    operating_region := operating_region,
                    opened_date := opened_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ
                AS rejected_at,

            'OPEN'
                AS resolution_status

        FROM raw.raw_branch

        WHERE opened_date IS NULL

        UNION ALL

        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BRANCH_STATUS_REFERENCE'
                AS rule_id,

            'HIGH'
                AS severity,

            'Branch status is not approved.'
                AS error_message,

            to_json(
                struct_pack(
                    branch_id := branch_id,
                    branch_code := branch_code,
                    branch_name := branch_name,
                    city := city,
                    state := state,
                    operating_region := operating_region,
                    opened_date := opened_date,
                    status := status
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ
                AS rejected_at,

            'OPEN'
                AS resolution_status

        FROM raw.raw_branch

        WHERE status NOT IN (
            'ACTIVE',
            'INACTIVE',
            'CLOSED'
        )
        """,
        [
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
        ],
    )

    raw_count = con.execute(
        """
        SELECT COUNT(*)
        FROM raw.raw_branch
        """
    ).fetchone()[0]

    valid_count = con.execute(
        """
        SELECT COUNT(*)
        FROM staging.stg_branch
        """
    ).fetchone()[0]

    rejected_count = con.execute(
        """
        SELECT COUNT(DISTINCT source_record_key)
        FROM quarantine.rejected_branch
        """
    ).fetchone()[0]

    rule_failures = con.execute(
        """
        SELECT COUNT(*)
        FROM quarantine.rejected_branch
        """
    ).fetchone()[0]

    con.close()

    print(f"Raw branches: {raw_count}")
    print(f"Valid branches: {valid_count}")
    print(f"Rejected branch records: {rejected_count}")
    print(f"Rule failures: {rule_failures}")


if __name__ == "__main__":
    main()