# Legacy Banking Data Migration Contract

## Business scenario

NorthStar Community Bank operates a legacy PostgreSQL reporting database.

The bank wants to migrate its customer, account, transaction, balance,
branch, and compliance-reporting data to a governed cloud analytics
warehouse.

This repository implements a production-style migration simulation using
synthetic banking data.

## Project objective

Build a controlled data migration that demonstrates:

- historical data migration
- incremental data migration
- deterministic watermark handling
- rejected-record quarantine
- technical and financial reconciliation
- idempotent reruns
- restartable pipeline execution
- metadata lineage and data classification
- cutover and rollback procedures

## Architecture decision

The project uses:

- Neon PostgreSQL as the managed legacy source
- Parquet files as the immutable landing layer
- DuckDB as the complete local analytical target
- BigQuery Sandbox for selected GCP demonstrations
- dbt Core for transformations and data tests
- Apache Airflow for orchestration
- OpenMetadata for governance and lineage
- Metabase for migration monitoring

The complete workflow must remain reproducible without paid cloud services.

## In scope

- customers
- accounts
- branches
- transactions
- daily account balances
- account status history
- AML alerts
- migration audit records
- rejected-record handling
- source-to-target reconciliation

## Out of scope

- real customer data
- real banking credentials
- actual payment processing
- production disaster recovery
- machine-learning fraud detection
- regulatory certification

## Critical data elements

- customer_id
- account_id
- transaction_id
- transaction_timestamp
- transaction_amount
- currency_code
- opening_balance
- debit_total
- credit_total
- closing_balance
- updated_at

## Acceptance criteria

### Completeness

Every source record must be:

1. loaded successfully,
2. quarantined with a documented reason, or
3. excluded through an approved migration rule.

### Financial integrity

For every account and business date:

opening_balance + credit_total - debit_total = closing_balance

Financial values must reconcile at their stored decimal precision.

### Incremental reliability

Records sharing the same timestamp must not be missed.

Incremental extraction will use a compound checkpoint:

(updated_at, record_key)

### Idempotency

Rerunning the same migration batch must not create duplicate business
records.

### Traceability

Every migrated row must retain:

- source system
- source table
- source record key
- migration batch ID
- source update timestamp
- ingestion timestamp
- record hash

### Restartability

A failed table or partition must restart without repeating successfully
completed work.

## Cost constraint

The default project setup must not require:

- a paid cloud subscription
- a billing-enabled Google Cloud project
- a permanent virtual machine
- paid orchestration
- paid metadata software
- paid dashboard software

## Honest positioning

This is a production-style portfolio simulation.

It does not represent a real banking migration and does not claim
regulatory approval.