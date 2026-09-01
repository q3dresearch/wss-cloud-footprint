"""Parser for schema aws-regional.v1 — the AWS regional services table.

The payload is set membership: one row per (service, region) pair, no numbers
in it at all. The measurement is therefore an *aggregate* — how many services
a region carries, how many regions a service has reached — so this parser
counts rather than reads.

entity_id is namespaced (`region:…`, `service:…`) because two different kinds
of entity share one table; without the prefix a region and a service could
collide in the observation space.
"""

import json
from collections import Counter

from wss import derive

PARSER_VERSION = "2"


def parse(body: bytes, ctx: derive.ParseContext):
    rows = json.loads(body)["prices"]
    per_region: Counter = Counter()
    per_service: Counter = Counter()

    for row in rows:
        attrs = row["attributes"]
        per_region[attrs["aws:region"]] += 1
        per_service[attrs["aws:serviceName"]] += 1

    for region, count in sorted(per_region.items()):
        yield derive.Observation(
            entity_id=f"region:{region}", metric="services_available", value=count, unit="count"
        )
    for service, count in sorted(per_service.items()):
        yield derive.Observation(
            entity_id=f"service:{service}", metric="regions_available", value=count, unit="count"
        )
    # Fleet-wide totals, so a single row shows the footprint at a glance.
    yield derive.Observation(entity_id="aws", metric="service_region_pairs", value=len(rows), unit="count")
    yield derive.Observation(entity_id="aws", metric="regions", value=len(per_region), unit="count")
    yield derive.Observation(entity_id="aws", metric="services", value=len(per_service), unit="count")

    # The membership matrix itself, one row per (region, service) pair.
    #
    # Counts alone answer "is this region catching up"; they cannot answer
    # "which services does this region lack", which is the question anyone
    # actually deploying asks. That answer was only reachable by re-parsing
    # raw/, so the derived layer was lossy for its own research questions.
    #
    # It is verbose — ~5,800 rows per capture, most identical week to week —
    # and that redundancy is the deliberate price of a self-sufficient
    # derived layer. If it ever outgrows git, emit on change instead.
    for row in sorted(rows, key=lambda r: (r["attributes"]["aws:region"], r["attributes"]["aws:serviceName"])):
        attrs = row["attributes"]
        yield derive.Observation(
            entity_id=f"region:{attrs['aws:region']}/service:{attrs['aws:serviceName']}",
            metric="available",
            value=1,
            unit="bool",
        )


derive.register("aws-regional.v1", parse, PARSER_VERSION)
