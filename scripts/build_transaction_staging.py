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

    # ---------------------------------------------------------
    # VALID TRANSACTIONS
    # ---------------------------------------------------------

    con.execute(
        """
        CREATE OR REPLACE TABLE staging.stg_transaction AS

        SELECT
            transaction_id,
            source_account_id,
            destination_account_id,
            transaction_ts AS transaction_timestamp_utc,
            UPPER(transaction_type) AS transaction_type,
            amount AS transaction_amount,
            UPPER(currency_code) AS currency_code,
            UPPER(payment_channel) AS payment_channel,
            aml_flag AS is_aml_flagged,

            migration_batch_id,
            source_system,
            source_table,
            source_record_key,
            source_updated_at,
            ingested_at,
            record_hash,
            schema_version,
            is_deleted

        FROM raw.raw_transaction AS t

        WHERE EXISTS (
            SELECT 1
            FROM core.dim_account AS a
            WHERE a.account_id = t.source_account_id
        )

        AND EXISTS (
            SELECT 1
            FROM core.dim_account AS a
            WHERE a.account_id = t.destination_account_id
        )

        AND amount > 0

        AND currency_code = 'INR'

        AND source_account_id <> destination_account_id

        AND transaction_type IN (
            'TRANSFER',
            'CARD_PAYMENT',
            'CASH_WITHDRAWAL',
            'DIRECT_DEBIT'
        )

        AND payment_channel IN (
            'MOBILE',
            'ONLINE',
            'ATM',
            'BRANCH',
            'CARD'
        )

        AND NOT EXISTS (
            SELECT 1
            FROM core.dim_account AS a
            WHERE a.account_id = t.source_account_id
              AND a.account_status = 'CLOSED'
              AND a.closed_date IS NOT NULL
              AND a.closed_date < CAST(t.transaction_ts AS DATE)
        )
        """
    )

    # ---------------------------------------------------------
    # REJECTED TRANSACTIONS
    # One row per failed rule.
    # ---------------------------------------------------------

    con.execute(
        """
        CREATE OR REPLACE TABLE quarantine.rejected_transaction AS

        -- Missing source account
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'TRANSACTION_SOURCE_ACCOUNT_REFERENCE'
                AS rule_id,

            'CRITICAL'
                AS severity,

            'Source account does not resolve to a valid account.'
                AS error_message,

            to_json(
                struct_pack(
                    transaction_id := transaction_id,
                    source_account_id := source_account_id,
                    destination_account_id := destination_account_id,
                    transaction_ts := transaction_ts,
                    transaction_type := transaction_type,
                    amount := amount,
                    currency_code := currency_code,
                    payment_channel := payment_channel,
                    aml_flag := aml_flag
                )
            ) AS raw_payload,

            ?::TIMESTAMPTZ AS rejected_at,

            'OPEN' AS resolution_status

        FROM raw.raw_transaction AS t

        WHERE NOT EXISTS (
            SELECT 1
            FROM core.dim_account AS a
            WHERE a.account_id = t.source_account_id
        )


        UNION ALL


        -- Missing destination account
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'TRANSACTION_DESTINATION_ACCOUNT_REFERENCE',
            'CRITICAL',

            'Destination account does not resolve to a valid account.',

            to_json(
                struct_pack(
                    transaction_id := transaction_id,
                    source_account_id := source_account_id,
                    destination_account_id := destination_account_id,
                    transaction_ts := transaction_ts,
                    transaction_type := transaction_type,
                    amount := amount,
                    currency_code := currency_code,
                    payment_channel := payment_channel,
                    aml_flag := aml_flag
                )
            ),

            ?::TIMESTAMPTZ,

            'OPEN'

        FROM raw.raw_transaction AS t

        WHERE NOT EXISTS (
            SELECT 1
            FROM core.dim_account AS a
            WHERE a.account_id = t.destination_account_id
        )


        UNION ALL


        -- Invalid amount
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'TRANSACTION_AMOUNT_POSITIVE',
            'HIGH',

            'Transaction amount must be greater than zero.',

            to_json(
                struct_pack(
                    transaction_id := transaction_id,
                    source_account_id := source_account_id,
                    destination_account_id := destination_account_id,
                    transaction_ts := transaction_ts,
                    transaction_type := transaction_type,
                    amount := amount,
                    currency_code := currency_code,
                    payment_channel := payment_channel,
                    aml_flag := aml_flag
                )
            ),

            ?::TIMESTAMPTZ,

            'OPEN'

        FROM raw.raw_transaction

        WHERE amount <= 0


        UNION ALL


        -- Invalid currency
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'TRANSACTION_CURRENCY_REFERENCE',
            'HIGH',

            'Transaction currency is not in the approved currency list.',

            to_json(
                struct_pack(
                    transaction_id := transaction_id,
                    source_account_id := source_account_id,
                    destination_account_id := destination_account_id,
                    transaction_ts := transaction_ts,
                    transaction_type := transaction_type,
                    amount := amount,
                    currency_code := currency_code,
                    payment_channel := payment_channel,
                    aml_flag := aml_flag
                )
            ),

            ?::TIMESTAMPTZ,

            'OPEN'

        FROM raw.raw_transaction

        WHERE currency_code <> 'INR'


        UNION ALL


        -- Source and destination are identical
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'TRANSACTION_ACCOUNTS_DIFFER',
            'HIGH',

            'Source and destination accounts must be different.',

            to_json(
                struct_pack(
                    transaction_id := transaction_id,
                    source_account_id := source_account_id,
                    destination_account_id := destination_account_id,
                    transaction_ts := transaction_ts,
                    transaction_type := transaction_type,
                    amount := amount,
                    currency_code := currency_code,
                    payment_channel := payment_channel,
                    aml_flag := aml_flag
                )
            ),

            ?::TIMESTAMPTZ,

            'OPEN'

        FROM raw.raw_transaction

        WHERE source_account_id = destination_account_id


        UNION ALL


        -- Invalid transaction type
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'TRANSACTION_TYPE_REFERENCE',
            'HIGH',

            'Transaction type is not approved.',

            to_json(
                struct_pack(
                    transaction_id := transaction_id,
                    source_account_id := source_account_id,
                    destination_account_id := destination_account_id,
                    transaction_ts := transaction_ts,
                    transaction_type := transaction_type,
                    amount := amount,
                    currency_code := currency_code,
                    payment_channel := payment_channel,
                    aml_flag := aml_flag
                )
            ),

            ?::TIMESTAMPTZ,

            'OPEN'

        FROM raw.raw_transaction

        WHERE transaction_type NOT IN (
            'TRANSFER',
            'CARD_PAYMENT',
            'CASH_WITHDRAWAL',
            'DIRECT_DEBIT'
        )


        UNION ALL


        -- Invalid payment channel
        SELECT
            migration_batch_id,
            source_system,
            source_table,
            source_record_key,

            'TRANSACTION_CHANNEL_REFERENCE',
            'HIGH',

            'Payment channel is not approved.',

            to_json(
                struct_pack(
                    transaction_id := transaction_id,
                    source_account_id := source_account_id,
                    destination_account_id := destination_account_id,
                    transaction_ts := transaction_ts,
                    transaction_type := transaction_type,
                    amount := amount,
                    currency_code := currency_code,
                    payment_channel := payment_channel,
                    aml_flag := aml_flag
                )
            ),

            ?::TIMESTAMPTZ,

            'OPEN'

        FROM raw.raw_transaction

        WHERE payment_channel NOT IN (
            'MOBILE',
            'ONLINE',
            'ATM',
            'BRANCH',
            'CARD'
        )


        UNION ALL


        -- Transaction after source account closure
        SELECT
            t.migration_batch_id,
            t.source_system,
            t.source_table,
            t.source_record_key,

            'CLOSED_ACCOUNT_TRANSACTION',
            'HIGH',

            'Transaction occurred after the source account was closed.',

            to_json(
                struct_pack(
                    transaction_id := t.transaction_id,
                    source_account_id := t.source_account_id,
                    destination_account_id := t.destination_account_id,
                    transaction_ts := t.transaction_ts,
                    transaction_type := t.transaction_type,
                    amount := t.amount,
                    currency_code := t.currency_code,
                    payment_channel := t.payment_channel,
                    aml_flag := t.aml_flag
                )
            ),

            ?::TIMESTAMPTZ,

            'OPEN'

        FROM raw.raw_transaction AS t

        JOIN core.dim_account AS a
            ON t.source_account_id = a.account_id

        WHERE a.account_status = 'CLOSED'
          AND a.closed_date IS NOT NULL
          AND a.closed_date < CAST(t.transaction_ts AS DATE)
        """,
        [
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
            rejected_at,
        ],
    )

    raw_count = con.execute(
        """
        SELECT COUNT(*)
        FROM raw.raw_transaction
        """
    ).fetchone()[0]

    valid_count = con.execute(
        """
        SELECT COUNT(*)
        FROM staging.stg_transaction
        """
    ).fetchone()[0]

    rejected_records = con.execute(
        """
        SELECT COUNT(DISTINCT source_record_key)
        FROM quarantine.rejected_transaction
        """
    ).fetchone()[0]

    rule_failures = con.execute(
        """
        SELECT COUNT(*)
        FROM quarantine.rejected_transaction
        """
    ).fetchone()[0]

    if raw_count != valid_count + rejected_records:
        con.close()

        raise RuntimeError(
            "Transaction reconciliation failed: "
            f"raw={raw_count}, "
            f"valid={valid_count}, "
            f"rejected={rejected_records}"
        )

    con.close()

    print(f"Raw transactions: {raw_count}")
    print(f"Valid transactions: {valid_count}")
    print(f"Rejected transaction records: {rejected_records}")
    print(f"Rule failures: {rule_failures}")
    print("Transaction count reconciliation passed")


if __name__ == "__main__":
    main()