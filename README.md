# Legacy Banking Data Migration

A production-style portfolio project demonstrating the controlled migration
of synthetic retail-banking data from PostgreSQL to a governed analytical
warehouse.

## Planned architecture

```text
Neon PostgreSQL
       |
       | Python extraction
       v
Immutable Parquet landing
       |
       v
DuckDB raw → staging → core
       |
       +-- dbt tests and transformations
       +-- reconciliation and quarantine
       +-- Airflow orchestration
       +-- OpenMetadata governance
       +-- Metabase dashboard
       |
       v
BigQuery Sandbox demonstration
```

## Target data layers

| Layer | Purpose |
|---|---|
| raw | Immutable source-shaped records with migration metadata |
| staging | Typed, standardised, deduplicated, and validated records |
| core | Business-ready dimensions and facts |
| quarantine | Rejected records with rules and source payloads |
| reconciliation | Count, relationship, and financial comparisons |

Detailed mappings are documented in:

`docs/source_to_target_mapping/core_mapping.md`