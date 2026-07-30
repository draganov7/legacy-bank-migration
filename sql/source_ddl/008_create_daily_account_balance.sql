CREATE TABLE IF NOT EXISTS finance.daily_account_balance (
    account_id BIGINT NOT NULL,
    business_date DATE NOT NULL,
    opening_balance NUMERIC(18, 2) NOT NULL,
    debit_total NUMERIC(18, 2) NOT NULL,
    credit_total NUMERIC(18, 2) NOT NULL,
    closing_balance NUMERIC(18, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    PRIMARY KEY (account_id, business_date),

    CONSTRAINT fk_daily_balance_account
        FOREIGN KEY (account_id)
        REFERENCES core.account(account_id),

    CONSTRAINT chk_daily_balance_debit
        CHECK (debit_total >= 0),

    CONSTRAINT chk_daily_balance_credit
        CHECK (credit_total >= 0),

    CONSTRAINT chk_daily_balance_equation
        CHECK (
            closing_balance
            = opening_balance + credit_total - debit_total
        ),

    CONSTRAINT chk_daily_balance_timestamps
        CHECK (updated_at >= created_at)
);

CREATE INDEX IF NOT EXISTS idx_daily_balance_business_date
    ON finance.daily_account_balance(business_date);