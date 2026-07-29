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