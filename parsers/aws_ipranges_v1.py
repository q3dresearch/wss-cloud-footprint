"""Parser for schema aws-ipranges.v1 — AWS's published IP ranges.

Also set membership: the measurement is how many prefixes a region or service
carries, so this parser counts. Same `region:` / `service:` namespacing as
aws-regional.v1, deliberately, so the two sources join on entity_id.

The file carries a `syncToken` (a unix timestamp of when AWS last published
it) — that is the fact's own date, so it becomes observed_at rather than
letting capture time stand in for it.
"""

import json
from collections import Counter
from datetime import datetime, timezone

from wss import derive

PARSER_VERSION = "1"


def parse(body: bytes, ctx: derive.ParseContext):
    data = json.loads(body)
    observed_at = None
    token = data.get("syncToken")
    if token and str(token).isdigit():
        observed_at = datetime.fromtimestamp(int(token), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    per_region: Counter = Counter()
    per_service: Counter = Counter()
    for prefix in data.get("prefixes", []):
        per_region[prefix["region"]] += 1
        per_service[prefix["service"]] += 1

    for region, count in sorted(per_region.items()):
        yield derive.Observation(
            entity_id=f"region:{region}", metric="ipv4_prefixes", value=count,
            unit="count", observed_at=observed_at,
        )
    for service, count in sorted(per_service.items()):
        yield derive.Observation(
            entity_id=f"service:{service}", metric="ipv4_prefixes", value=count,
            unit="count", observed_at=observed_at,
        )
    yield derive.Observation(
        entity_id="aws", metric="ipv4_prefixes_total", value=len(data.get("prefixes", [])),
        unit="count", observed_at=observed_at,
    )
    yield derive.Observation(
        entity_id="aws", metric="ipv6_prefixes_total", value=len(data.get("ipv6_prefixes", [])),
        unit="count", observed_at=observed_at,
    )


derive.register("aws-ipranges.v1", parse, PARSER_VERSION)
