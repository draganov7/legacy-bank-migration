CREATE TABLE IF NOT EXISTS control.defect_manifest (
    defect_id VARCHAR(50) PRIMARY KEY,
    source_table VARCHAR(200) NOT NULL,
    source_record_key VARCHAR(200) NOT NULL,
    rule_id VARCHAR(100) NOT NULL,
    defect_description TEXT NOT NULL,
    expected_handling VARCHAR(50) NOT NULL,
    injected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);