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
        CREATE OR REPLACE TABLE staging.stg_daily_account_balance AS

        WITH balance_with_previous AS (
            SELECT
                balance.*,

                LAG(closing_balance) OVER (
                    PARTITION BY account_id
                    ORDER BY business_date
                ) AS previous_closing_balance

            FROM raw.raw_daily_account_balance AS balance
        )

        SELECT
            account_id,
            business_date,
            opening_balance,
            debit_total,
            credit_total,
            closing_balance,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM balance_with_previous AS balance

        WHERE EXISTS (
            SELECT 1
            FROM core.dim_account AS account
            WHERE account.account_id = balance.account_id
        )

        AND debit_total >= 0

        AND credit_total >= 0

        AND (
            opening_balance
            + credit_total
            - debit_total
        ) = closing_balance

        AND (
            previous_closing_balance IS NULL
            OR opening_balance = previous_closing_balance
        )
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE quarantine.rejected_daily_balance AS

        -- Missing account
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BALANCE_ACCOUNT_REFERENCE' AS rule_id,
            'CRITICAL' AS severity,

            'Balance account_id does not resolve to a valid account.'
                AS error_message,

            to_json(
                struct_pack(
                    account_id := account_id,
                    business_date := business_date,
                    opening_balance := opening_balance,
                    debit_total := debit_total,
                    credit_total := credit_total,
                    closing_balance := closing_balance
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,
            'OPEN' AS resolution_status

        FROM raw.raw_daily_account_balance AS balance

        WHERE NOT EXISTS (
            SELECT 1
            FROM core.dim_account AS account
            WHERE account.account_id = balance.account_id
        )


        UNION ALL


        -- Negative debit
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BALANCE_DEBIT_NON_NEGATIVE',
            'HIGH',

            'Debit total must be non-negative.',

            to_json(
                struct_pack(
                    account_id := account_id,
                    business_date := business_date,
                    opening_balance := opening_balance,
                    debit_total := debit_total,
                    credit_total := credit_total,
                    closing_balance := closing_balance
                )
            ),

            ?::TIMESTAMPTZ,
            'OPEN'

        FROM raw.raw_daily_account_balance

        WHERE debit_total < 0


        UNION ALL


        -- Negative credit
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BALANCE_CREDIT_NON_NEGATIVE',
            'HIGH',

            'Credit total must be non-negative.',

            to_json(
                struct_pack(
                    account_id := account_id,
                    business_date := business_date,
                    opening_balance := opening_balance,
                    debit_total := debit_total,
                    credit_total := credit_total,
                    closing_balance := closing_balance
                )
            ),

            ?::TIMESTAMPTZ,
            'OPEN'

        FROM raw.raw_daily_account_balance

        WHERE credit_total < 0


        UNION ALL


        -- Balance equation failure
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BALANCE_EQUATION',
            'CRITICAL',

            'Opening balance plus credits minus debits does not equal closing balance.',

            to_json(
                struct_pack(
                    account_id := account_id,
                    business_date := business_date,
                    opening_balance := opening_balance,
                    debit_total := debit_total,
                    credit_total := credit_total,
                    closing_balance := closing_balance
                )
            ),

            ?::TIMESTAMPTZ,
            'OPEN'

        FROM raw.raw_daily_account_balance

        WHERE (
            opening_balance
            + credit_total
            - debit_total
        ) <> closing_balance


        UNION ALL


        -- Roll-forward failure
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'BALANCE_ROLL_FORWARD',
            'CRITICAL',

            'Current opening balance does not equal previous closing balance.',

            to_json(
                struct_pack(
                    account_id := account_id,
                    business_date := business_date,
                    opening_balance := opening_balance,
                    debit_total := debit_total,
                    credit_total := credit_total,
                    closing_balance := closing_balance
                )
            ),

            ?::TIMESTAMPTZ,
            'OPEN'

        FROM (
            SELECT
                balance.*,

                LAG(closing_balance) OVER (
                    PARTITION BY account_id
                    ORDER BY business_date
                ) AS previous_closing_balance

            FROM raw.raw_daily_account_balance AS balance
        ) AS ordered

        WHERE previous_closing_balance IS NOT NULL
          AND opening_balance <> previous_closing_balance
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
        "SELECT COUNT(*) FROM raw.raw_daily_account_balance"
    ).fetchone()[0]

    valid_count = con.execute(
        "SELECT COUNT(*) FROM staging.stg_daily_account_balance"
    ).fetchone()[0]

    rejected_records = con.execute(
        """
        SELECT COUNT(DISTINCT source_record_key)
        FROM quarantine.rejected_daily_balance
        """
    ).fetchone()[0]

    rule_failures = con.execute(
        """
        SELECT COUNT(*)
        FROM quarantine.rejected_daily_balance
        """
    ).fetchone()[0]

    if raw_count != valid_count + rejected_records:
        con.close()
        raise RuntimeError(
            "Daily balance reconciliation failed: "
            f"raw={raw_count}, "
            f"valid={valid_count}, "
            f"rejected={rejected_records}"
        )

    con.close()

    print(f"Raw balances: {raw_count}")
    print(f"Valid balances: {valid_count}")
    print(f"Rejected balance records: {rejected_records}")
    print(f"Rule failures: {rule_failures}")
    print("Daily balance count reconciliation passed")


if __name__ == "__main__":
    main()