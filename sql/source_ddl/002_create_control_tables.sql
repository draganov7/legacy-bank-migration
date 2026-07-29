CREATE TABLE IF NOT EXISTS control.migration_batch (
    batch_id UUID PRIMARY KEY,
    migration_type VARCHAR(30) NOT NULL,
    lower_watermark TIMESTAMPTZ,
    upper_watermark TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    initiated_by VARCHAR(100),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS control.table_run (
    batch_id UUID NOT NULL,
    table_name VARCHAR(200) NOT NULL,
    source_rows BIGINT,
    extracted_rows BIGINT,
    loaded_rows BIGINT,
    rejected_rows BIGINT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,

    PRIMARY KEY (batch_id, table_name),

    CONSTRAINT fk_table_run_batch
        FOREIGN KEY (batch_id)
        REFERENCES control.migration_batch(batch_id)
);

CREATE TABLE IF NOT EXISTS control.source_extract_control (
    source_table VARCHAR(200) PRIMARY KEY,
    last_watermark_ts TIMESTAMPTZ,
    last_watermark_key VARCHAR(200),
    last_successful_batch_id UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_extract_control_batch
        FOREIGN KEY (last_successful_batch_id)
        REFERENCES control.migration_batch(batch_id)
);