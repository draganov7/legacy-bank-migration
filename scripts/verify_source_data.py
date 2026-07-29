import os

import psycopg
from dotenv import load_dotenv


EXPECTED_COUNTS = {
    "core.branch": 5,
    "core.customer": 50,
    "core.account": 75,
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


if __name__ == "__main__":
    main()