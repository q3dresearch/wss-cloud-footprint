-- Analytics over the long-format observation table.
--   observations(series_id, entity_id, observed_at, captured_at, metric,
--                value, unit, source_id, raw_ref, parser_version)
-- Run with: python examples/load_observations.py
-- Or in DuckDB, straight off GitHub with no credentials:
--   SELECT * FROM read_csv_auto('https://raw.githubusercontent.com/q3dresearch/wss-cloud-footprint/main/derived/observations/*.csv')

-- Every query starts by deduplicating. A source whose payload carries its own
-- date (AWS ip-ranges has a syncToken) restates the same observed_at whenever
-- the publisher has not republished, so a naive filter double-counts. `latest`
-- keeps the most recent statement of each fact.

-- Region maturity: what you give up by deploying outside the biggest region.
WITH latest AS (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
      PARTITION BY series_id, entity_id, metric, observed_at
      ORDER BY captured_at DESC) AS rn
    FROM observations
  ) WHERE rn = 1
)
SELECT substr(entity_id, 8) AS region, CAST(value AS INTEGER) AS services_available
FROM latest
WHERE metric = 'services_available'
  AND observed_at = (SELECT MAX(observed_at) FROM latest WHERE metric = 'services_available')
ORDER BY services_available DESC;

-- Exactly which services a region is missing, against the fullest region.
-- Change the region code to the one you are evaluating.
WITH latest AS (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
      PARTITION BY series_id, entity_id, metric, observed_at
      ORDER BY captured_at DESC) AS rn
    FROM observations
  ) WHERE rn = 1
),
m AS (
  SELECT substr(entity_id, 8, instr(entity_id, '/service:') - 8) AS region,
         substr(entity_id, instr(entity_id, '/service:') + 9)    AS service
  FROM latest
  WHERE metric = 'available'
    AND observed_at = (SELECT MAX(observed_at) FROM latest WHERE metric = 'available')
)
SELECT service AS missing_from_eusc_de_east_1
FROM m WHERE region = 'us-east-1'
EXCEPT
SELECT service FROM m WHERE region = 'eusc-de-east-1'
ORDER BY 1;

-- The opening kit: services present in every region, i.e. what a new region
-- is guaranteed to have on day one.
WITH latest AS (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
      PARTITION BY series_id, entity_id, metric, observed_at
      ORDER BY captured_at DESC) AS rn
    FROM observations
  ) WHERE rn = 1
)
SELECT substr(entity_id, 9) AS service, CAST(value AS INTEGER) AS regions
FROM latest
WHERE metric = 'regions_available'
  AND observed_at = (SELECT MAX(observed_at) FROM latest WHERE metric = 'regions_available')
ORDER BY regions ASC, service;

-- Declared interconnection capacity per network: breadth against depth.
WITH latest AS (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
      PARTITION BY series_id, entity_id, metric, observed_at
      ORDER BY captured_at DESC) AS rn
    FROM observations
  ) WHERE rn = 1
),
cap AS (SELECT substr(entity_id, 5) AS net, CAST(value AS REAL) AS mbps FROM latest
        WHERE metric = 'declared_capacity_total'
          AND observed_at = (SELECT MAX(observed_at) FROM latest WHERE metric = 'declared_capacity_total')),
ex  AS (SELECT substr(entity_id, 5) AS net, CAST(value AS REAL) AS n FROM latest
        WHERE metric = 'exchanges_present'
          AND observed_at = (SELECT MAX(observed_at) FROM latest WHERE metric = 'exchanges_present'))
SELECT cap.net,
       ROUND(cap.mbps / 1e6, 1)          AS tbps_declared,
       CAST(ex.n AS INTEGER)             AS exchanges,
       ROUND(cap.mbps / ex.n / 1000, 0)  AS gbps_per_exchange
FROM cap JOIN ex ON ex.net = cap.net
ORDER BY tbps_declared DESC;

-- Shared or owned: is a metro split between networks, or held by one?
-- A disaster-recovery metro with one network present is not multi-vendor.
WITH latest AS (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
      PARTITION BY series_id, entity_id, metric, observed_at
      ORDER BY captured_at DESC) AS rn
    FROM observations
  ) WHERE rn = 1
),
city AS (SELECT entity_id AS ix, value AS metro FROM latest WHERE metric = 'city'
         AND observed_at = (SELECT MAX(observed_at) FROM latest WHERE metric = 'city')),
cap AS (
  -- dedup alone is not enough here: also pin to the newest capture, or the
  -- sum runs across every week ever captured
  SELECT substr(entity_id, 5, instr(entity_id, '/ix:') - 5) AS net,
         'ix:' || substr(entity_id, instr(entity_id, '/ix:') + 4) AS ix,
         CAST(value AS REAL) AS mbps
  FROM latest
  WHERE metric = 'declared_capacity'
    AND observed_at = (SELECT MAX(observed_at) FROM latest WHERE metric = 'declared_capacity')
),
per AS (
  SELECT city.metro, cap.net, SUM(cap.mbps) AS mbps
  FROM cap JOIN city ON city.ix = cap.ix
  GROUP BY city.metro, cap.net
),
tot AS (SELECT metro, SUM(mbps) AS total FROM per GROUP BY metro),
lead AS (
  SELECT metro, net, mbps,
         ROW_NUMBER() OVER (PARTITION BY metro ORDER BY mbps DESC) AS rn
  FROM per
)
SELECT tot.metro,
       ROUND(tot.total / 1e6, 1)                    AS tbps,
       (SELECT COUNT(*) FROM per WHERE per.metro = tot.metro) AS networks,
       lead.net                                     AS leader,
       ROUND(lead.mbps * 100.0 / tot.total, 0)      AS leader_pct
FROM tot JOIN lead ON lead.metro = tot.metro AND lead.rn = 1
WHERE tot.total > 1e6
ORDER BY tot.total DESC;
