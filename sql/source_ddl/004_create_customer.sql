CREATE TABLE IF NOT EXISTS core.customer (
    customer_id BIGINT PRIMARY KEY,
    customer_number VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    date_of_birth DATE NOT NULL,
    email VARCHAR(254),
    phone VARCHAR(30),
    address_line_1 VARCHAR(200),
    address_line_2 VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country_code CHAR(2) NOT NULL,
    kyc_status VARCHAR(20) NOT NULL,
    customer_status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT chk_customer_kyc_status
        CHECK (
            kyc_status IN (
                'PENDING',
                'VERIFIED',
                'REVIEW_REQUIRED',
                'REJECTED'
            )
        ),

    CONSTRAINT chk_customer_status
        CHECK (
            customer_status IN (
                'ACTIVE',
                'INACTIVE',
                'BLOCKED',
                'CLOSED'
            )
        ),

    CONSTRAINT chk_customer_country_code
        CHECK (country_code = UPPER(country_code)),

    CONSTRAINT chk_customer_dates
        CHECK (updated_at >= created_at)
);