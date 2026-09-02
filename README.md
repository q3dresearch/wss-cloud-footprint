# wss-cloud-footprint

**Where the internet's infrastructure is actually being built** — captured
weekly, because nobody publishes the history.

AWS tells you which services are live in which regions *today*. PeeringDB
tells you where nine major networks have plugged in *today*. Neither keeps
yesterday's answer, and neither offers a window to page back through. So the
date a service reached a region, or the week a network doubled its capacity
in São Paulo, is unrecoverable — unless somebody was writing it down.

This repo writes it down.

> **One thing to read before using the capacity numbers.** PeeringDB records
> **public** peering only. Enterprise cloud traffic disproportionately runs
> over private interconnects — Direct Connect, ExpressRoute, Cloud
> Interconnect — which appear nowhere here and which nobody publishes. So
> content and edge networks (Meta, Akamai, Cloudflare) rank high *correctly*,
> because pushing video to consumers is exactly what public exchanges are
> for, while AWS's and Azure's true footprint is larger than shown. Read
> every figure as **declared public interconnection capacity** — a real,
> comparable quantity — never as traffic or total bandwidth.

## The questions

The point of this repo is the questions, not the folders. Every source exists
to answer one; a source that answers none should be dropped, and a question
nothing answers is the next thing to build. **Append freely** — an open
question with no data is a useful entry, not a gap to hide.

Status: **open** (nothing captured) · **accruing** (captured, needs weeks) ·
**answerable** (enough data) · **blocked** (needs something we lack).

| # | Question | Status |
| --- | --- | --- |
| Q1 | When a provider opens a region, how long until it reaches service parity — and which regions never do? | accruing (~12 weeks) |
| Q2 | Which services **stall**? A service stuck in few regions for months is being quietly abandoned, which matters if you depend on it. | accruing (~12 weeks) |
| Q3 | Is an advertised region count backed by real infrastructure, or is it a press release? | partly answerable |
| Q4 | **Where is accelerator capacity going?** Which regions get GPU/TPU instance types first? | blocked — see below |
| Q5 | Does address space lead or lag service availability — do the addresses arrive before the services? | accruing |
| Q6 | What is the **opening kit**, the services treated as a minimum viable region, and is it growing? | answerable (102 services) |
| Q7 | For a given region, exactly which services are missing? The deployability question. | answerable |
| Q8 | Where is interconnection concentrated, and which metros does a vendor skip? A DR metro with one network present is not multi-vendor. | answerable |
| Q9 | Is capacity growth leading or trailing region launches — do the ports arrive before the services? | accruing |

**Q4 is blocked on credentials, not effort.** Instance types per region are
not public: AWS's EC2 pricing index is small but only points at per-region
offer files of hundreds of megabytes, and `DescribeInstanceTypeOfferings`
answers it exactly but needs AWS keys. The engine supports authenticated
sources, so this is a decision about running with a read-only AWS key — not a
dead end.

## What you can build from it

Everything below is rendered by [examples/visualize.py](examples/visualize.py)
from the derived CSVs — stdlib only, deterministic, no network, no map
package.

![Shared, or owned?](examples/charts/metro-concentration.svg)

**Q8 — saturation at the core, dominance at the edge.** Across 85 metros above
1 Tbps the median leader holds 29%, but the spread is the finding. Amsterdam,
Frankfurt and Sydney sit near 18–20% with all nine networks present;
Fortaleza (65%) and Jakarta (46%) are effectively one network's territory.

![Two ways to build a network](examples/charts/network-strategy.svg)

**Q3 — same capacity, opposite strategies.** Cloudflare reaches 355 exchanges
at ~146 Gbps each; Meta reaches 209 at ~369. Colour is what a network *is*,
because identity is already on every label.

![What a new region still lacks](examples/charts/region-gap.svg)

**Q6 and Q7 — every region ships with the same 102-service opening kit**, then
accumulates the remaining 93 over years. `eusc-de-east-1`, the European
Sovereign Cloud, is 90 services short of `us-east-1`. If you are choosing
where to deploy, that gap is the answer.

![The rollout frontier](examples/charts/rollout-frontier.svg)

**Q2 — what is still moving, and what has stalled.** For anything in six
regions or fewer the regions are named outright, because at that size the
list is the finding.

![Declared capacity over time](examples/charts/capacity-history.svg)

**Q9, deliberately empty.** No history exists to import, so the series can
only start the day capture started. The chart renders itself once four
weekly captures exist.

## Using it

The files to query are `derived/observations/<YYYY-MM>.csv`, long format:

```
series_id, entity_id, observed_at, captured_at, metric, value, unit, source_id, raw_ref, parser_version
```

`entity_id` is namespaced so every source joins on it:

| entity_id | from | metrics |
| --- | --- | --- |
| `region:us-east-1` | AWS | `services_available`, `ipv4_prefixes` |
| `service:Amazon S3` | AWS | `regions_available` |
| `region:<r>/service:<s>` | AWS | `available` — the membership matrix |
| `ix:<id>` | PeeringDB | `city`, `country`, `continent`, `networks_present` |
| `net:aws` | PeeringDB | `declared_capacity_total`, `ports_total`, `exchanges_present` |
| `net:aws/ix:<id>` | PeeringDB | `declared_capacity`, `ports` |
| `metro:<cc>/<city>` | PeeringDB | `latitude`, `longitude`, `facilities` |

```bash
head derived/observations/*.csv
python examples/load_observations.py     # sqlite + example queries
python examples/visualize.py             # regenerate every chart
duckdb -c "SELECT * FROM read_csv_auto('derived/observations/*.csv') LIMIT 5"
```

Coverage dates are machine-readable in [health/health.csv](health/health.csv)
(`first_success_at` → `last_success_at`). Five sources, all weekly: AWS
services-by-region and IP ranges; PeeringDB exchanges, capacity and facility
coordinates.

`capture-weekly` (Mondays 22:25 UTC) → `health` → `derive`, powered by the
[wss](https://github.com/neldivad/wss-engine) engine pinned to one version.
No workflow names a source.

## Contributing, and what is next

**The test for a new source: which open question does it close?** If the
answer is "none", it does not go in — add the question first and justify it,
or drop the idea. That rule is what stopped this repo collecting four more
vendors' IP-range files, which were trivial to fetch and would have answered
nothing.

By that test the remaining work is narrow:

- **Q3** wants per-region service depth for a second vendor. Azure publishes a
  products-by-region page (HTML); GCP's regions page redirects. Both need
  `wss explore` to find a JSON endpoint behind them.
- **Q4** wants instance-type catalogues, and needs an AWS key.
- **Q8/Q9** are already served — they need Mondays, not endpoints.
- A **world map** is a short build once facility coordinates land: latitude
  and longitude *are* the projection, so 2,066 datacenter cities trace the
  populated world with no basemap dependency.

Adding a source is one file in `registry/` and, if the payload shape is new,
one parser. Nothing else changes — no workflow edits.

A note on manners: **PeeringDB is a volunteer-run non-profit**, not a vendor
API. Requests are spaced 15 seconds apart on a weekly cadence, and both
endpoints request an explicit `fields=` list so operator contact details are
never fetched at all. If you fork this, keep that.

## Licences

Code MIT ([LICENSE](LICENSE)); data CC-BY-4.0 ([LICENSE-DATA](LICENSE-DATA)).
Captured content comes from public AWS endpoints (subject to the
[AWS service terms](https://aws.amazon.com/service-terms/)) and from
[PeeringDB](https://www.peeringdb.com/) — whose terms should be verified
before redistributing derived data commercially.

Topics: `git-scraping` · `open-data` · `point-in-time-data` · `dataset`
