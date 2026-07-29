import argparse
import csv
import hashlib
import json
import random
from datetime import date, datetime, time, timezone
from pathlib import Path

from faker import Faker


DEFAULT_SEED = 20260726
REFERENCE_DATE = date(2026, 7, 26)
OUTPUT_DIRECTORY = Path("data/generated")


def utc_timestamp(value: date) -> str:
    return datetime.combine(
        value,
        time(hour=9),
        tzinfo=timezone.utc,
    ).isoformat()


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)

    return digest.hexdigest()


def generate_branches(
    fake: Faker,
    count: int,
) -> list[dict[str, object]]:
    regions = [
        ("Mumbai", "Maharashtra", "WEST"),
        ("Pune", "Maharashtra", "WEST"),
        ("Bengaluru", "Karnataka", "SOUTH"),
        ("Chennai", "Tamil Nadu", "SOUTH"),
        ("Delhi", "Delhi", "NORTH"),
    ]

    branches = []

    for branch_id in range(1, count + 1):
        city, state, region = regions[(branch_id - 1) % len(regions)]
        opened_date = fake.date_between(
            start_date=date(1995, 1, 1),
            end_date=date(2018, 12, 31),
        )

        branches.append(
            {
                "branch_id": branch_id,
                "branch_code": f"NSB-{branch_id:03d}",
                "branch_name": f"NorthStar {city} Branch",
                "city": city,
                "state": state,
                "operating_region": region,
                "opened_date": opened_date.isoformat(),
                "status": "ACTIVE",
                "created_at": utc_timestamp(opened_date),
                "updated_at": utc_timestamp(opened_date),
            }
        )

    return branches


def generate_customers(
    fake: Faker,
    count: int,
) -> list[dict[str, object]]:
    kyc_statuses = [
        "VERIFIED",
        "VERIFIED",
        "VERIFIED",
        "PENDING",
        "REVIEW_REQUIRED",
    ]

    customer_statuses = [
        "ACTIVE",
        "ACTIVE",
        "ACTIVE",
        "INACTIVE",
    ]

    customers = []

    for customer_id in range(1, count + 1):
        full_name = fake.name()
        created_date = fake.date_between(
            start_date=date(2015, 1, 1),
            end_date=date(2025, 12, 31),
        )
        updated_date = fake.date_between(
            start_date=created_date,
            end_date=REFERENCE_DATE,
        )

        customers.append(
            {
                "customer_id": customer_id,
                "customer_number": f"CUST-{customer_id:08d}",
                "full_name": full_name,
                "date_of_birth": fake.date_of_birth(
                    minimum_age=21,
                    maximum_age=75,
                ).isoformat(),
                "email": (
                    f"customer{customer_id:05d}@example.com"
                ),
                "phone": fake.numerify("+91-9#########"),
                "address_line_1": fake.street_address(),
                "address_line_2": "",
                "city": fake.city(),
                "state": fake.state(),
                "postal_code": fake.postcode(),
                "country_code": "IN",
                "kyc_status": random.choice(kyc_statuses),
                "customer_status": random.choice(customer_statuses),
                "created_at": utc_timestamp(created_date),
                "updated_at": utc_timestamp(updated_date),
            }
        )

    return customers


def generate_accounts(
    fake: Faker,
    count: int,
    customer_count: int,
    branch_count: int,
) -> list[dict[str, object]]:
    account_types = [
        "SAVINGS",
        "SAVINGS",
        "CURRENT",
        "LOAN",
        "CREDIT_CARD",
    ]

    account_statuses = [
        "ACTIVE",
        "ACTIVE",
        "ACTIVE",
        "DORMANT",
        "FROZEN",
        "CLOSED",
    ]

    accounts = []

    for account_id in range(1, count + 1):
        opened_date = fake.date_between(
            start_date=date(2016, 1, 1),
            end_date=date(2025, 12, 31),
        )
        status = random.choice(account_statuses)

        closed_date = ""
        if status == "CLOSED":
            closed_date = fake.date_between(
                start_date=opened_date,
                end_date=REFERENCE_DATE,
            ).isoformat()

        updated_date = fake.date_between(
            start_date=opened_date,
            end_date=REFERENCE_DATE,
        )

        accounts.append(
            {
                "account_id": account_id,
                "account_number": f"NS{account_id:014d}",
                "customer_id": random.randint(1, customer_count),
                "branch_id": random.randint(1, branch_count),
                "account_type": random.choice(account_types),
                "currency_code": "INR",
                "opened_date": opened_date.isoformat(),
                "closed_date": closed_date,
                "status": status,
                "created_at": utc_timestamp(opened_date),
                "updated_at": utc_timestamp(updated_date),
            }
        )

    return accounts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--branches", type=int, default=5)
    parser.add_argument("--customers", type=int, default=50)
    parser.add_argument("--accounts", type=int, default=75)
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)

    fake = Faker("en_IN")
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    branches = generate_branches(fake, args.branches)
    customers = generate_customers(fake, args.customers)
    accounts = generate_accounts(
        fake,
        args.accounts,
        args.customers,
        args.branches,
    )

    files = {
        "branches": (
            OUTPUT_DIRECTORY / "branches.csv",
            branches,
        ),
        "customers": (
            OUTPUT_DIRECTORY / "customers.csv",
            customers,
        ),
        "accounts": (
            OUTPUT_DIRECTORY / "accounts.csv",
            accounts,
        ),
    }

    for name, (path, rows) in files.items():
        write_csv(path, rows, list(rows[0].keys()))
        print(f"Generated {len(rows)} rows: {path}")

    manifest = {
        "seed": args.seed,
        "reference_date": REFERENCE_DATE.isoformat(),
        "generated_at_note": (
            "Files are deterministic for the recorded seed and parameters."
        ),
        "datasets": {
            name: {
                "file": path.name,
                "row_count": len(rows),
                "sha256": calculate_sha256(path),
            }
            for name, (path, rows) in files.items()
        },
    }

    manifest_path = OUTPUT_DIRECTORY / "generation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Generated manifest: {manifest_path}")


if __name__ == "__main__":
    main()