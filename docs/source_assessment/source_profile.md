# Minimal Source Profiling Report

## Row counts

| Table | Rows |
|---|---:|
| core.branch | 5 |
| core.customer | 50 |
| core.account | 75 |
| payments.bank_transaction | 500 |
| finance.daily_account_balance | 994 |

## Key and relationship checks

| Check | Failures |
|---|---:|
| Duplicate customer IDs | 0 |
| Duplicate account IDs | 0 |
| Duplicate transaction IDs | 0 |
| Accounts without customers | 0 |
| Transactions with missing accounts | 0 |

## Transaction profile

| Metric | Value |
|---|---|
| Earliest transaction | 2016-02-18 18:55:29+00:00 |
| Latest transaction | 2026-07-25 06:02:05+00:00 |
| Total transaction amount | 1287507.31 |

## Financial checks

| Check | Result |
|---|---:|
| Balance equation failures | 0 |
| Roll-forward failures | 0 |
| Total transaction amount | 1287507.31 |
| Total balance debits | 1287507.31 |
| Total balance credits | 1287507.31 |

## Conclusion

This report represents the clean source baseline before controlled defects
are introduced.
