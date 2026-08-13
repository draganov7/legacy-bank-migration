# Transaction Reconciliation Report

## Run

- Run timestamp: 2026-08-11T07:07:15.637033+00:00

## Row counts

| Metric | Value |
|---|---:|
| Source rows | 500 |
| Raw rows | 500 |
| Valid staging rows | 483 |
| Rejected distinct records | 17 |
| Core rows | 483 |

## Amount reconciliation

| Metric | Amount |
|---|---:|
| Source amount | 1287507.31 |
| Raw amount | 1287507.31 |
| Valid staging amount | 1241114.94 |
| Rejected amount | 46392.37 |
| Core amount | 1241114.94 |

## AML reconciliation

| Metric | Count |
|---|---:|
| Source AML flagged | 14 |
| Raw AML flagged | 14 |
| Core AML flagged | 14 |

## Transaction type comparison

| Type | Source count | Source amount | Core count | Core amount |
|---|---:|---:|---:|---:|
| CARD_PAYMENT | 94 | 213834.83 | 94 | 213834.83 |
| CASH_WITHDRAWAL | 98 | 254027.52 | 93 | 243630.39 |
| DIRECT_DEBIT | 97 | 270703.15 | 94 | 259818.39 |
| TRANSFER | 211 | 548941.81 | 202 | 523831.33 |

## Check results

| Check | Source | Target | Variance | Status |
|---|---:|---:|---:|---|
| source_vs_raw_row_count | 500 | 500 | 0 | PASS |
| raw_vs_valid_plus_rejected | 500 | 500 | 0 | PASS |
| staging_vs_core_row_count | 483 | 483 | 0 | PASS |
| source_vs_raw_amount | 1287507.31 | 1287507.31 | 0.00 | PASS |
| raw_vs_core_plus_rejected_amount | 1287507.31 | 1287507.31 | 0.00 | PASS |
| staging_vs_core_amount | 1241114.94 | 1241114.94 | 0.00 | PASS |
| source_vs_raw_aml_count | 14 | 14 | 0 | PASS |

## Summary

Failed reconciliation checks: 0
