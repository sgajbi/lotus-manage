CREATE INDEX IF NOT EXISTS idx_dpm_mandate_snapshots_portfolio_version_numeric
    -- Issue #646. mandate_version is TEXT holding str(binding_version), so
    -- ordering by it directly is lexicographic and puts "9" above "10". The
    -- temporal reads order by magnitude instead, and this index matches the
    -- leading part of that expression. The 0019 index remains for callers
    -- ordering by the raw column.
    --
    -- This is deliberately a strict PREFIX of the query's ORDER BY: it stops
    -- after the normalized digits and leaves the raw mandate_version and
    -- mandate_id tie-breakers to an incremental sort. Including them would put
    -- two full copies of the version text in one B-tree tuple, which is worth
    -- avoiding because B-tree entries have a size limit. Those tie-breakers
    -- only separate versions of equal magnitude, such as '01' and '1'.
    --
    -- MEASURED on PostgreSQL 17.6, 1000 rows for one portfolio, ANALYZE run
    -- (this is a plan observation on one shape, not a general performance
    -- claim):
    --   with this index    Index Scan + Incremental Sort, presorted on
    --                      as_of_date and both magnitude expressions,
    --                      2 rows touched, 12 buffers, 0.566 ms
    --   without it         Bitmap Heap Scan over all 1000 matching rows then
    --                      a top-N heapsort, 97 heap blocks, 7.986 ms
    -- So the index is genuinely used and the LIMIT stops early rather than
    -- every matching row being read and sorted.
    --
    -- It does NOT make arbitrarily long version text indexable, and nothing
    -- here should be read as claiming that. Measured with incompressible
    -- random digit strings: 2000 digits accepted, 2700 refused with
    -- "index row size 2752 exceeds btree version 4 maximum 2704". The index
    -- that refuses is idx_dpm_mandate_snapshots_portfolio_temporal, from
    -- migration 0019 which is already on main - so this ceiling predates this
    -- index and this index does not lower it. Highly repetitive versions go
    -- much further because they compress; 20000 identical digits were
    -- accepted. Compressibility is not a property the storage contract
    -- promises, so the honest bound is the incompressible one.
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
