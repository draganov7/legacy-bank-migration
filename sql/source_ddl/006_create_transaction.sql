CREATE TABLE IF NOT EXISTS payments.bank_transaction (
    transaction_id BIGINT PRIMARY KEY,
    source_account_id BIGINT NOT NULL,
    destination_account_id BIGINT NOT NULL,
    transaction_ts TIMESTAMPTZ NOT NULL,
    transaction_type VARCHAR(30) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency_code CHAR(3) NOT NULL,
    payment_channel VARCHAR(20) NOT NULL,
    aml_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_transaction_source_account
        FOREIGN KEY (source_account_id)
        REFERENCES core.account(account_id),

    CONSTRAINT fk_transaction_destination_account
        FOREIGN KEY (destination_account_id)
        REFERENCES core.account(account_id),

    CONSTRAINT chk_transaction_accounts_differ
        CHECK (source_account_id <> destination_account_id),

    CONSTRAINT chk_transaction_type
        CHECK (
            transaction_type IN (
                'TRANSFER',
                'CARD_PAYMENT',
                'CASH_WITHDRAWAL',
                'DIRECT_DEBIT'
            )
        ),

    CONSTRAINT chk_transaction_amount
        CHECK (amount > 0),

    CONSTRAINT chk_transaction_currency
        CHECK (
            currency_code = UPPER(currency_code)
            AND CHAR_LENGTH(currency_code) = 3
        ),

    CONSTRAINT chk_payment_channel
        CHECK (
            payment_channel IN (
                'MOBILE',
                'ONLINE',
                'ATM',
                'BRANCH',
                'CARD'
            )
        ),

    CONSTRAINT chk_transaction_timestamps
        CHECK (
            updated_at >= created_at
            AND created_at >= transaction_ts
        )
);

CREATE INDEX IF NOT EXISTS idx_transaction_updated_at
    ON payments.bank_transaction(updated_at, transaction_id);

CREATE INDEX IF NOT EXISTS idx_transaction_source_account
    ON payments.bank_transaction(source_account_id);

CREATE INDEX IF NOT EXISTS idx_transaction_destination_account
    ON payments.bank_transaction(destination_account_id);