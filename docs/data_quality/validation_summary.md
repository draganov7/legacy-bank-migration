# Source Validation Summary

## Validation run

- Source system: Neon PostgreSQL
- Run timestamp: 2026-08-03T16:26:48.036571+00:00
- Validation stage: pre-migration source assessment

## Results

| Source table | Rejected records |
|---|---:|
| core.customer | 2 |
| payments.bank_transaction | 8 |
| **Total** | **10** |

## Rules evaluated

| Rule ID | Severity | Expected records |
|---|---|---:|
| CUSTOMER_DOB_NOT_FUTURE | HIGH | 1 |
| CUSTOMER_EMAIL_FORMAT | HIGH | 1 |
| TRANSACTION_CURRENCY_REFERENCE | HIGH | 1 |
| CLOSED_ACCOUNT_TRANSACTION | HIGH | 1 |

## Quarantine behavior

Rejected records retain:

- source system
- source table
- source record key
- rule ID
- severity
- error message
- raw source payload
- rejection timestamp
- resolution status

The local JSON Lines files are ignored by Git because they contain
record-level source data. Only this summary is committed as portfolio
evidence.
