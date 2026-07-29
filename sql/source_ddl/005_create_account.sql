CREATE TABLE IF NOT EXISTS core.account (
    account_id BIGINT PRIMARY KEY,
    account_number VARCHAR(34) NOT NULL UNIQUE,
    customer_id BIGINT NOT NULL,
    branch_id BIGINT NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    currency_code CHAR(3) NOT NULL,
    opened_date DATE NOT NULL,
    closed_date DATE,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_account_customer
        FOREIGN KEY (customer_id)
        REFERENCES core.customer(customer_id),

    CONSTRAINT fk_account_branch
        FOREIGN KEY (branch_id)
        REFERENCES core.branch(branch_id),

    CONSTRAINT chk_account_type
        CHECK (
            account_type IN (
                'SAVINGS',
                'CURRENT',
                'LOAN',
                'CREDIT_CARD'
            )
        ),

    CONSTRAINT chk_account_status
        CHECK (
            status IN (
                'ACTIVE',
                'DORMANT',
                'FROZEN',
                'CLOSED'
            )
        ),

    CONSTRAINT chk_account_currency
        CHECK (
            currency_code = UPPER(currency_code)
            AND CHAR_LENGTH(currency_code) = 3
        ),

    CONSTRAINT chk_account_closed_date
        CHECK (
            closed_date IS NULL
            OR closed_date >= opened_date
        ),

    CONSTRAINT chk_account_timestamps
        CHECK (updated_at >= created_at)
);