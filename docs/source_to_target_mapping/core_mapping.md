# Source-to-Target Mapping

## Purpose

This document defines how source data from Neon PostgreSQL will be mapped
into the DuckDB analytical target.

The target follows these layers:

- raw: source-shaped records with migration metadata
- staging: typed, standardised, deduplicated, and validated records
- core: business-ready dimensions and facts
- quarantine: rejected records and validation details
- reconciliation: batch-level counts and financial comparisons

## Common migration metadata

Every raw target record will contain:

| Target column | Type | Rule |
|---|---|---|
| migration_batch_id | VARCHAR | Assigned when the extraction batch starts |
| source_system | VARCHAR | Constant value `neon_postgresql` |
| source_table | VARCHAR | Original schema and table name |
| source_record_key | VARCHAR | Source primary key converted to text |
| source_updated_at | TIMESTAMP | Copied from source `updated_at` |
| ingested_at | TIMESTAMP | UTC timestamp when loaded into raw |
| record_hash | VARCHAR | SHA-256 hash of canonical business columns |
| schema_version | VARCHAR | Initial value `1.0` |
| is_deleted | BOOLEAN | Initial value `FALSE` |

---

# Customer mapping

## Raw table

Target:

```text
raw.raw_customer