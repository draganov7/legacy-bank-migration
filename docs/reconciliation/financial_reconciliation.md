# Financial Reconciliation Report

## Run

- Run timestamp: 2026-08-12T12:28:00.582843+00:00

## Source totals

| Metric | Value |
|---|---:|
| Transaction rows | 500 |
| Transaction amount | 1287507.31 |
| Balance rows | 994 |
| Debit total | 1287507.31 |
| Credit total | 1287507.31 |

## Raw target totals

| Metric | Value |
|---|---:|
| Transaction rows | 500 |
| Transaction amount | 1287507.31 |
| Balance rows | 994 |
| Debit total | 1287507.31 |
| Credit total | 1287507.31 |

## Accepted target totals

| Metric | Value |
|---|---:|
| Transaction rows | 483 |
| Transaction amount | 1241114.94 |
| Balance rows | 985 |
| Debit total | 1280076.91 |
| Credit total | 1275084.97 |

## Quarantine

| Metric | Value |
|---|---:|
| Rejected transaction records | 17 |
| Rejected balance records | 9 |

## Critical checks

| Check | Expected | Actual | Variance | Status |
|---|---:|---:|---:|---|
| source_transaction_vs_debits | 1287507.31 | 1287507.31 | 0.00 | PASS |
| source_transaction_vs_credits | 1287507.31 | 1287507.31 | 0.00 | PASS |
| source_vs_raw_transaction_count | 500 | 500 | 0 | PASS |
| source_vs_raw_transaction_amount | 1287507.31 | 1287507.31 | 0.00 | PASS |
| source_vs_raw_balance_count | 994 | 994 | 0 | PASS |
| source_vs_raw_debit_total | 1287507.31 | 1287507.31 | 0.00 | PASS |
| source_vs_raw_credit_total | 1287507.31 | 1287507.31 | 0.00 | PASS |
| raw_transaction_vs_debits | 1287507.31 | 1287507.31 | 0.00 | PASS |
| raw_transaction_vs_credits | 1287507.31 | 1287507.31 | 0.00 | PASS |
| raw_balance_rows_vs_core_plus_rejected | 994 | 994 | 0 | PASS |
| core_balance_equation_failures | 0 | 0 | 0 | PASS |
| core_roll_forward_failures | 0 | 0 | 0 | PASS |

## Accepted cross-fact comparison

| Metric | Variance |
|---|---:|
| Core balance debits minus accepted transaction amount | 38961.97 |
| Core balance credits minus accepted transaction amount | 33970.03 |

The accepted transaction and balance totals are reported separately because
transactions rejected for referential-quality reasons may still contribute
to source daily balances for otherwise valid accounts.

This variance is therefore not automatically classified as a migration
failure. It must be explained through the rejected-record population.

## Summary

Failed critical checks: 0
