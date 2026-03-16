CREATE TYPE bank_code AS ENUM ('itau', 'c6bank');
CREATE TYPE simulation_status AS ENUM ('RECEIVED', 'PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'CANCELLED');

CREATE TABLE simulations (
    id UUID PRIMARY KEY,
    bank bank_code NOT NULL,
    status simulation_status NOT NULL,
    input_payload JSONB NOT NULL,
    idempotency_key VARCHAR(64),
    correlation_id VARCHAR(64),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX uq_simulations_bank_idempotency ON simulations (bank, idempotency_key);
CREATE INDEX ix_simulations_status ON simulations (status);
CREATE INDEX ix_simulations_created_at ON simulations (created_at DESC);

CREATE TABLE simulation_results (
    id UUID PRIMARY KEY,
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    raw_result JSONB,
    normalized_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_simulation_results_simulation_id ON simulation_results (simulation_id);

CREATE TABLE simulation_events (
    id UUID PRIMARY KEY,
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    status simulation_status NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_simulation_events_simulation_id ON simulation_events (simulation_id);
