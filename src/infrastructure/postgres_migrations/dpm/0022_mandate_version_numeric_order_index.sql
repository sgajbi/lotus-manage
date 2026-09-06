CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_portfolio_version_numeric
    -- Issue #646. mandate_version is TEXT holding str(binding_version), so
    -- ordering by it directly is lexicographic and puts "9" above "10". The
    -- temporal reads order numerically instead, and this index matches that
    -- expression so the comparison stays indexed rather than forcing a scan.
    -- The 0019 index remains for callers ordering by the raw column.
    --
    -- Every element below must match the query's ORDER BY exactly, including
    -- NULLS LAST and the mandate_version tie-breaker. PostgreSQL defaults DESC
    -- to NULLS FIRST, so an index written as plain DESC has the opposite null
    -- ordering to the query and cannot satisfy it; the planner then sorts
    -- anyway and the index silently buys nothing. The tie-breaker matters for
    -- the same reason: the query falls through to mandate_version DESC when
    -- two versions are numerically equal, as '01' and '1' are.
    --
    -- Note for future migrations in this repo: the statement splitter is not
    -- comment-aware, so a semicolon inside a comment truncates the statement.
    ON dpm_mandate_snapshots (
        portfolio_id,
        as_of_date DESC,
        (CASE WHEN mandate_version ~ '^[0-9]+$' THEN mandate_version::numeric ELSE NULL END)
            DESC NULLS LAST,
        mandate_version DESC,
        mandate_id DESC
    );

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_mandate_version_numeric
    -- The same expression for the mandate_id-keyed reads, which order by
    -- as_of_date DESC, the numeric expression, then mandate_version DESC.
    ON dpm_mandate_snapshots (
        mandate_id,
        as_of_date DESC,
        (CASE WHEN mandate_version ~ '^[0-9]+$' THEN mandate_version::numeric ELSE NULL END)
            DESC NULLS LAST,
        mandate_version DESC
    );
