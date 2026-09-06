CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_portfolio_version_numeric
    -- Issue #646. mandate_version is TEXT holding str(binding_version), so
    -- ordering by it directly is lexicographic and puts "9" above "10". The
    -- temporal reads order by magnitude instead, and this index matches that
    -- expression so the comparison stays indexed rather than forcing a scan.
    -- The 0019 index remains for callers ordering by the raw column.
    --
    -- Every element below must match _MANDATE_VERSION_ORDER in
    -- src/infrastructure/mandates/postgres.py exactly, including NULLS LAST,
    -- the COLLATE "C" clauses, and the raw mandate_version tie-breaker.
    -- PostgreSQL defaults DESC to NULLS FIRST, so an index written as plain
    -- DESC has the opposite null ordering to the query and cannot satisfy it.
    -- The planner then sorts anyway and the index silently buys nothing. The
    -- tie-breaker matters for the same reason: the query falls through to
    -- mandate_version when two versions have equal magnitude, as '01' and '1'
    -- do.
    --
    -- Length-then-digits rather than a cast, because the storage contract is
    -- unrestricted TEXT. A cast bounds it, and here that bound would be worse
    -- than a failed read: a row exceeding it fails this CREATE INDEX and
    -- blocks startup for every caller.
    --
    -- The statement splitter skips comments whole, so a semicolon inside one
    -- is safe. It was not always: this file previously carried a warning to
    -- avoid them, which is the wrong half of the fix, so the splitter learned
    -- about comments instead.
    ON dpm_mandate_snapshots (
        portfolio_id,
        as_of_date DESC,
        (
            CASE WHEN mandate_version ~ '^[0-9]+$'
                 THEN length(COALESCE(NULLIF(ltrim(mandate_version, '0'), ''), '0'))
                 ELSE NULL END
        ) DESC NULLS LAST,
        (
            CASE WHEN mandate_version ~ '^[0-9]+$'
                 THEN COALESCE(NULLIF(ltrim(mandate_version, '0'), ''), '0')
                 ELSE NULL END
        ) COLLATE "C" DESC NULLS LAST,
        mandate_version COLLATE "C" DESC,
        mandate_id DESC
    );

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_mandate_version_numeric
    -- The same expression for the mandate_id-keyed reads, which order by
    -- as_of_date DESC, the magnitude elements, then mandate_version.
    ON dpm_mandate_snapshots (
        mandate_id,
        as_of_date DESC,
        (
            CASE WHEN mandate_version ~ '^[0-9]+$'
                 THEN length(COALESCE(NULLIF(ltrim(mandate_version, '0'), ''), '0'))
                 ELSE NULL END
        ) DESC NULLS LAST,
        (
            CASE WHEN mandate_version ~ '^[0-9]+$'
                 THEN COALESCE(NULLIF(ltrim(mandate_version, '0'), ''), '0')
                 ELSE NULL END
        ) COLLATE "C" DESC NULLS LAST,
        mandate_version COLLATE "C" DESC
    );
