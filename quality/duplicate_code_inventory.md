# lotus-manage Duplicate Implementation Inventory

- Detector: exact normalized Python function-body duplicates.
- Scope: `src, scripts`.
- Minimum function size: `8` lines.
- Gate posture: active non-regression gate via `make duplicate-implementation-gate`; existing groups are explicitly baselined and future exact duplicate groups fail.

## Current Duplicate Groups

### Group 1

- Fingerprint: `847ede373a8c35ca9ffc13af638fafc6d1c8133fa7656e09e7f086ef3cd36b2c`

| File | Function | Line | Lines |
| --- | --- | --- | --- |
| `scripts/generate_rfc0041_wave_evidence.py` | `_request` | 46 | 16 |
| `scripts/generate_rfc0042_outcome_evidence.py` | `_request` | 46 | 16 |
