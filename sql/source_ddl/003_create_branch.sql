CREATE TABLE IF NOT EXISTS core.branch (
    branch_id BIGINT PRIMARY KEY,
    branch_code VARCHAR(20) NOT NULL UNIQUE,
    branch_name VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    operating_region VARCHAR(50) NOT NULL,
    opened_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT chk_branch_status
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'CLOSED')),

    CONSTRAINT chk_branch_dates
        CHECK (updated_at >= created_at)
);