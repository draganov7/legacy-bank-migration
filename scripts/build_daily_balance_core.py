import os

import duckdb
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    duckdb_path = os.getenv("DUCKDB_PATH")

    if not duckdb_path:
        raise RuntimeError("DUCKDB_PATH is not set")

    con = duckdb.connect(duckdb_path)

    con.execute("CREATE SCHEMA IF NOT EXISTS core")

    con.execute(
        """
        CREATE OR REPLACE TABLE core.fct_daily_balance AS

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

        FROM staging.stg_daily_account_balance
        """
    )

    staging_count = con.execute(
        """
        SELECT COUNT(*)
        FROM staging.stg_daily_account_balance
        """
    ).fetchone()[0]

    core_count = con.execute(
        """
        SELECT COUNT(*)
        FROM core.fct_daily_balance
        """
    ).fetchone()[0]

    duplicate_count = con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                account_id,
                business_date
            FROM core.fct_daily_balance
            GROUP BY
                account_id,
                business_date
            HAVING COUNT(*) > 1
        ) AS duplicates
        """
    ).fetchone()[0]

    missing_accounts = con.execute(
        """
        SELECT COUNT(*)
        FROM core.fct_daily_balance AS balance
        LEFT JOIN core.dim_account AS account
            ON balance.account_id = account.account_id
        WHERE account.account_id IS NULL
        """
    ).fetchone()[0]

    balance_failures = con.execute(
        """
        SELECT COUNT(*)
        FROM core.fct_daily_balance
        WHERE (
            opening_balance
            + credit_total
            - debit_total
        ) <> closing_balance
        """
    ).fetchone()[0]

    if staging_count != core_count:
        con.close()
        raise RuntimeError(
            "Staging/core balance counts do not match"
        )

    if duplicate_count != 0:
        con.close()
        raise RuntimeError(
            f"Duplicate balance keys found: {duplicate_count}"
        )

    if missing_accounts != 0:
        con.close()
        raise RuntimeError(
            f"Balances with missing accounts: {missing_accounts}"
        )

    if balance_failures != 0:
        con.close()
        raise RuntimeError(
            f"Balance equation failures: {balance_failures}"
        )

    con.close()

    print(f"Staging balances: {staging_count}")
    print(f"Core balances: {core_count}")
    print("Duplicate balance keys: 0")
    print("Balances with missing accounts: 0")
    print("Balance equation failures: 0")
    print("Daily balance fact build verified successfully")


if __name__ == "__main__":
    main()