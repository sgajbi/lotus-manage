-- Legacy admissions remain readable but have no authority for protected Risk calls.
ALTER TABLE dpm_wave_simulation_operations
    ADD COLUMN risk_authority_context_json JSONB,
    ADD COLUMN risk_authority_context_hash TEXT,
    ADD CONSTRAINT dpm_wave_simulation_risk_context_pair CHECK (
        (risk_authority_context_json IS NULL AND risk_authority_context_hash IS NULL)
        OR (risk_authority_context_json IS NOT NULL AND risk_authority_context_hash IS NOT NULL)
    );
