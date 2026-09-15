# Data shape

*Generated 2026-09-15T13:14:08Z by `wss schema` from the derived rows. Do not hand-edit — regenerate after any derive.*

**You should not need to download anything to read this.**

- **230,995 observations** across 1 partition(s), in **6 series**
  - `aws.infra.ip-ranges` — 576 rows, **71 entities**
  - `aws.services.regional` — 78,860 rows, **6070 entities**
  - `azure.servicetags.public` — 26,210 rows, **3322 entities**
  - `peeringdb.exchanges.directory` — 71,394 rows, **1323 entities**
  - `peeringdb.facilities.geo` — 25,128 rows, **2094 entities**
  - `peeringdb.networks.capacity` — 28,827 rows, **1597 entities**
- Raw: 31 file(s), 19,947,251 bytes on disk, 5 capture date(s), 2026-09-01 → 2026-09-09

## Sources

| source | cadence | endpoints | storage | personal data | licence |
| --- | --- | ---: | --- | --- | --- |
| `aws.infra.ip-ranges` | weekly | 1 | git | none | public AWS endpoint; see https://aws.amazon.com/service-term |
| `aws.services.regional` | weekly | 1 | git | none | public AWS endpoint; see https://aws.amazon.com/service-term |
| `azure.servicetags.public` | weekly | 1 | git | none | Microsoft publishes this openly for firewall configuration |
| `peeringdb.exchanges.directory` | weekly | 1 | git | none | PeeringDB API; see https://www.peeringdb.com/ terms — VERIFY |
| `peeringdb.facilities.geo` | weekly | 1 | git | none | PeeringDB API; see https://www.peeringdb.com/ terms — VERIFY |
| `peeringdb.networks.capacity` | weekly | 1 | git | none | PeeringDB API; see https://www.peeringdb.com/ terms — VERIFY |

## Columns

```
series_id, entity_id, observed_at, captured_at, metric, value, unit, source_id, raw_ref, parser_version
```

`entity_id` looks like: **aws.infra.ip-ranges** `aws`, `region:GLOBAL`, `region:af-south-1`; **aws.services.regional** `aws`, `region:af-south-1`, `region:af-south-1/service:AD Connector`; **azure.servicetags.public** `feed:azure_servicetags`, `tag:ActionGroup`, `tag:ActionGroup.AustraliaCentral`; **peeringdb.exchanges.directory** `ix:1`, `ix:100`, `ix:1002`; **peeringdb.facilities.geo** `metro:AE/Abu Dhabi`, `metro:AE/Dubai`, `metro:AE/Jebel Ali`; **peeringdb.networks.capacity** `net:akamai`, `net:akamai/ix:1`, `net:akamai/ix:100`

## Metrics

| metric | series | rows | entities | type | unit | distinct | range / samples |
| --- | --- | ---: | ---: | --- | --- | ---: | --- |
| `available` | aws.services.regional | 75,805 | 5837 | bool | bool | 1 | `1` |
| `change_number` | azure.servicetags.public | 2 | 1 | number | count | 1 | `417` … `417` |
| `city` | peeringdb.exchanges.directory | 11,899 | 1323 | text | ref | 736 | `/`, `Abidjan`, `Abuja` |
| `continent` | peeringdb.exchanges.directory | 11,899 | 1323 | text | ref | 7 | `Africa`, `Asia Pacific`, `Australia` |
| `country` | peeringdb.exchanges.directory | 11,899 | 1323 | text | ref | 171 | `AE`, `AF`, `AL` |
| `declared_capacity` | peeringdb.networks.capacity | 14,292 | 1588 | number | Mbps | 40 | `0` … `8000000` |
| `declared_capacity_total` | peeringdb.networks.capacity | 81 | 9 | number | Mbps | 11 | `4510000` … `81416000` |
| `exchanges_present` | peeringdb.networks.capacity | 81 | 9 | number | count | 9 | `34` … `355` |
| `facilities` | peeringdb.exchanges.directory, peeringdb.facilities.geo | 18,181 | 3417 | number | count | 45 | `0` … `242` |
| `ipv4_prefixes` | aws.infra.ip-ranges | 560 | 70 | number | count | 101 | `1` … `6011` |
| `ipv4_prefixes_total` | aws.infra.ip-ranges | 8 | 1 | number | count | 5 | `10520` … `10549` |
| `ipv6_prefixes_total` | aws.infra.ip-ranges | 8 | 1 | number | count | 6 | `6237` … `6912` |
| `ix_name` | peeringdb.exchanges.directory | 11,899 | 1323 | text | ref | 1328 | `1-BG FREE`, `1-CZ FREE`, `1-DE FREE` |
| `latitude` | peeringdb.facilities.geo | 6,282 | 2094 | number | deg | 2088 | `-82.8628` … `65.6763` |
| `longitude` | peeringdb.facilities.geo | 6,282 | 2094 | number | deg | 2088 | `-158.0869` … `178.0274` |
| `networks_at_facilities` | peeringdb.facilities.geo | 6,282 | 2094 | number | count | 205 | `0` … `2388` |
| `networks_present` | peeringdb.exchanges.directory | 11,899 | 1323 | number | count | 289 | `0` … `1860` |
| `ports` | peeringdb.networks.capacity | 14,292 | 1588 | number | count | 6 | `1` … `6` |
| `ports_total` | peeringdb.networks.capacity | 81 | 9 | number | count | 11 | `39` … `440` |
| `prefix_count` | azure.servicetags.public | 6,642 | 3321 | number | count | 213 | `1` … `3114` |
| `prefix_count_v6` | azure.servicetags.public | 6,642 | 3321 | number | count | 107 | `0` … `1294` |
| `prefixes_total` | azure.servicetags.public | 2 | 1 | number | count | 1 | `95623` … `95623` |
| `region` | azure.servicetags.public | 6,434 | 3217 | text | name | 77 | `australiacentral`, `australiacentral2`, `australiaeast` |
| `regions` | aws.services.regional | 13 | 1 | number | count | 1 | `37` … `37` |
| `regions_available` | aws.services.regional | 2,535 | 195 | number | count | 30 | `3` … `37` |
| `regions_total` | azure.servicetags.public | 2 | 1 | number | count | 1 | `77` … `77` |
| `service` | azure.servicetags.public | 6,482 | 3241 | text | name | 97 | `ActionGroup`, `ApplicationInsightsAvail`, `AutonomousDevelopmentPla` |
| `service_region_pairs` | aws.services.regional | 13 | 1 | number | count | 3 | `5823` … `5836` |
| `services` | aws.services.regional | 13 | 1 | number | count | 1 | `195` … `195` |
| `services_available` | aws.services.regional | 481 | 37 | number | count | 35 | `105` … `195` |
| `services_total` | azure.servicetags.public | 2 | 1 | number | count | 1 | `97` … `97` |
| `tags_total` | azure.servicetags.public | 2 | 1 | number | count | 1 | `3321` … `3321` |

## Partitions

- `derived/observations/2026-09.csv.gz`
