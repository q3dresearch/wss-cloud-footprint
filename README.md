<h1 align="center">wss-cloud-footprint</h1>

<p align="center">
  <strong>Where the internet's infrastructure is actually being built, captured weekly</strong>
</p>

<div align="center">

  <a href="https://github.com/neldivad/wss-cloud-footprint/actions/workflows/capture-weekly.yml"><img alt="capture status" src="https://img.shields.io/github/actions/workflow/status/neldivad/wss-cloud-footprint/capture-weekly.yml?label=capture&style=flat-square"></a>
  <a href="https://github.com/neldivad/wss-cloud-footprint/commits"><img alt="last capture" src="https://img.shields.io/github/last-commit/neldivad/wss-cloud-footprint?label=last%20capture&style=flat-square"></a>
  <a href="https://github.com/neldivad/wss-cloud-footprint/blob/main/LICENSE"><img alt="licence" src="https://img.shields.io/github/license/neldivad/wss-cloud-footprint?style=flat-square"></a>
  <a href="https://github.com/neldivad/wss-cloud-footprint"><img alt="stars" src="https://img.shields.io/github/stars/neldivad/wss-cloud-footprint?style=social"></a>

</div>

<p align="center">
  <sub>fleet: <a href="https://github.com/neldivad/wss-engine">engine</a> · <a href="https://github.com/neldivad/wss-hugging-face">hugging face</a> · <a href="https://github.com/neldivad/wss-openrouter">openrouter</a> · <strong>cloud footprint</strong> · <a href="https://github.com/neldivad/wss-mining-pipeline">mining</a></sub>
</p>

AWS tells you which services are live in which regions *today*. PeeringDB
tells you where nine major networks have plugged in *today*. Neither keeps
yesterday's answer. So the date a service reached a region, or the week a
network doubled its capacity in São Paulo, is lost unless somebody wrote it
down. This repo writes it down.

> **Before using the capacity numbers:** PeeringDB records **public** peering
> only. Enterprise clouds move much of their traffic over private
> interconnects (Direct Connect, ExpressRoute) that appear nowhere here. So
> Meta and Akamai outranking AWS is correct *for public exchanges*, and not a
> claim about total bandwidth. Read every figure as **declared public
> interconnection capacity**, never as traffic.

## Questions this exists to answer

A source that answers no question gets dropped. A question nothing answers is
the next thing to build. Append freely.

| # | Question | Status |
| --- | --- | --- |
| Q1 | How long does a new region take to reach service parity? | needs ~12 weeks |
| Q2 | Which services have stalled mid-rollout? | needs ~12 weeks |
| Q3 | Is an advertised region count real infrastructure or a press release? | partly answerable |
| Q4 | Where is GPU/accelerator capacity going? | blocked — needs an AWS key |
| Q5 | Do addresses arrive in a region before services do? | accruing |
| Q6 | What is the minimum viable region — the "opening kit"? | answered: 102 services |
| Q7 | Exactly which services is a given region missing? | answerable |
| Q8 | Which metros are shared, and which are one network's territory? | answered |
| Q9 | Do interconnection ports arrive before region launches? | accruing |

## What you can build

All charts come from [examples/visualize.py](examples/visualize.py) — stdlib
only, deterministic, no map package.

![Shared, or owned?](examples/charts/metro-concentration.svg)

**Q8:** saturation at the core, dominance at the edge. Amsterdam and Frankfurt
sit near 18% with all nine networks present; Fortaleza is 65% one network.

![Two ways to build a network](examples/charts/network-strategy.svg)

**Q3:** Cloudflare reaches 355 exchanges at ~146 Gbps each, Meta 209 at ~369.
Same capacity, opposite strategies.

![What a new region still lacks](examples/charts/region-gap.svg)

**Q6/Q7:** every region ships the same 102-service opening kit, then
accumulates the rest over years. The EU Sovereign Cloud is 90 services short
of us-east-1.

![The rollout frontier](examples/charts/rollout-frontier.svg)

**Q2:** what is still spreading, and what has stopped. Services in six regions
or fewer get those regions named.

![Declared capacity over time](examples/charts/capacity-history.svg)

**Q9, deliberately empty.** No history exists to import, so the series starts
the day capture started. Fills in after four weekly captures.

## Using it

**Reading this data needs nothing** — no key, no account, no clone:

```bash
B=https://raw.githubusercontent.com/neldivad/wss-cloud-footprint/main/derived/observations
duckdb -c "SELECT * FROM read_csv_auto('$B/2026-09.csv') LIMIT 5"
```

One gotcha: a source whose payload carries its own date restates the same
`observed_at` when the publisher has not republished, so deduplicate on
`(series_id, entity_id, metric, observed_at)` taking the latest `captured_at`.
Every query in [examples/queries.sql](examples/queries.sql) shows the pattern.

```bash
head derived/observations/*.csv          # the data: one row per entity/metric/day
python examples/load_observations.py     # sqlite + example queries
python examples/visualize.py             # regenerate every chart
```

Columns are `series_id, entity_id, observed_at, captured_at, metric, value,
unit, source_id, raw_ref, parser_version`. `entity_id` is namespaced
(`region:us-east-1`, `net:aws/ix:26`, `metro:BR/São Paulo`) so every source
joins on it. Coverage dates live in [health/health.csv](health/health.csv).

Five weekly sources — AWS services-by-region and IP ranges; PeeringDB
exchanges, capacity and facility coordinates — captured Mondays 22:25 UTC by
the [wss](https://github.com/neldivad/wss-engine) engine.

## Contributing

**The test for a new source: which open question does it close?** If none, it
does not go in. That rule is what stopped this repo collecting four more
vendors' IP-range files — easy to fetch, would have answered nothing.

Adding one is a single file in `registry/`, plus a parser if the payload shape
is new. No workflow edits, ever.

One source is currently **auto-disabled**: `peeringdb.facilities.geo` needs a
free PeeringDB API key (its unfiltered endpoint rejects anonymous callers).
The other four are healthy.

Still open: Q3 wants service depth for a second vendor (Azure and GCP both
need an API found behind their HTML). Q4 needs an AWS key. A world map is a
short build once facility coordinates land — latitude and longitude *are* the
projection.

**Manners:** PeeringDB is a volunteer-run non-profit. Requests are 15 seconds
apart, weekly, use an explicit `fields=` list so operator contact details are
never fetched, and run in a **single shard** — sharding parallelises across
sources, so more shards would mean more runners hitting one host at the same
moment. Keep all of that if you fork.

## Licences

Code MIT; data CC-BY-4.0. Sources: public AWS endpoints
([terms](https://aws.amazon.com/service-terms/)) and
[PeeringDB](https://www.peeringdb.com/), whose terms should be checked before
redistributing derived data commercially.
