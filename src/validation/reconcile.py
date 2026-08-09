import duckdb

DB_PATH = "data/migration.duckdb"

con = duckdb.connect(DB_PATH)

result = con.execute("""
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT payment_id) AS unique_payment_ids,
        COUNT(*) - COUNT(payment_id) AS null_payment_ids
    FROM payments
""").fetchone()

print(f"Row count: {result[0]}")
print(f"Unique payment IDs: {result[1]}")
print(f"NULL payment IDs: {result[2]}")

con.close()