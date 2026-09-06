CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_portfolio_version_numeric
    -- Issue #646. mandate_version is TEXT holding str(binding_version), so
    -- ordering by it directly is lexicographic and puts "9" above "10". The
    -- temporal reads order by magnitude instead, and this index matches the
    -- leading part of that expression so the comparison stays indexed rather
    -- than forcing a full sort. The 0019 index remains for callers ordering by
    -- the raw column.
    --
    -- This is deliberately a strict PREFIX of the query's ORDER BY: it stops
    -- after the normalized digits and leaves the raw mandate_version and
    -- mandate_id tie-breakers to an incremental sort. Including them would put
    -- two full copies of the version text in one B-tree tuple, and B-tree
    -- entries have a page-dependent size limit, so a long-but-legal version
    -- that the existing single-copy index accepts could fail this CREATE INDEX
    -- during startup, or fail later inserts. Those tie-breakers only separate
    -- versions of equal magnitude, such as '01' and '1', so leaving them to the
    -- sort costs nothing on the common path.
    --
    -- What is here must still match _MANDATE_VERSION_ORDER in
    -- src/infrastructure/mandates/postgres.py element for element, including
    -- NULLS LAST and COLLATE "C". PostgreSQL defaults DESC to NULLS FIRST, so
    -- an index written as plain DESC has the opposite null ordering to the
    -- query and cannot satisfy it. The planner then sorts anyway and the index
    -- silently buys nothing.
    --
    -- Length-then-digits rather than a cast, because the storage contract is
    -- unrestricted TEXT and every cast bounds it.
    --
    -- The statement splitter skips comments whole, so a semicolon inside one is
    -- safe. It was not always: this file previously carried a warning to avoid
    -- them, which is the wrong half of the fix, so the splitter learned about
    -- comments instead.
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
        ) COLLATE "C" DESC NULLS LAST
    );

CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_mandate_version_numeric
    -- The same prefix for the mandate_id-keyed reads, for the same reasons.
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
        ) COLLATE "C" DESC NULLS LAST
    );
