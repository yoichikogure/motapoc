CREATE TABLE IF NOT EXISTS admin.app_user (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role_name TEXT NOT NULL DEFAULT 'admin',
    full_name TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin.import_job (
    import_job_id BIGSERIAL PRIMARY KEY,
    dataset_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    success_rows INTEGER NOT NULL DEFAULT 0,
    error_rows INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    validation_summary_json JSONB,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin.import_error (
    import_error_id BIGSERIAL PRIMARY KEY,
    import_job_id BIGINT NOT NULL REFERENCES admin.import_job(import_job_id) ON DELETE CASCADE,
    row_number INTEGER,
    error_message TEXT NOT NULL,
    raw_row_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin.system_parameter (
    parameter_key TEXT PRIMARY KEY,
    parameter_value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'number',
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.governorate (
    governorate_id INTEGER PRIMARY KEY,
    governorate_code TEXT UNIQUE NOT NULL,
    governorate_name_en TEXT NOT NULL,
    governorate_name_ar TEXT
);
