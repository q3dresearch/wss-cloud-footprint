"""Parsers for PeeringDB — the location layer and the capacity layer.

Shapes verified against the live API on 2026-09-02.

  pdb-exchanges.v1  one row per internet exchange: which metro it is in, how
                    many networks and facilities it has
  pdb-capacity.v1   declared port capacity per (network, exchange)

WHAT `speed` IS AND IS NOT. It is the capacity an operator says it has
provisioned at an exchange, in Mbps. It is **not** measured traffic — nobody
publishes that per location. Treat it as a commitment signal: an operator
does not pay for 100G ports it has no intention of filling. Any chart built
on it must say "declared capacity", never "bandwidth used".

Both requests use an explicit `fields=` list, because the full exchange
record carries operator contact emails. Those are never fetched, so they can
never reach the archive — the cheapest possible way to honour
`personal_data: none`.
"""

import json
from collections import defaultdict

from wss import derive

PARSER_VERSION = "1"

# ASN -> the name people recognise. Anything unlisted still parses; it just
# carries its ASN as the label.
NETWORKS = {
    16509: "aws",
    15169: "google",
    8075: "microsoft",
    13335: "cloudflare",
    54113: "fastly",
    32934: "meta",
    31898: "oracle",
    14061: "digitalocean",
    20940: "akamai",
}


def parse_exchanges(body: bytes, ctx: derive.ParseContext):
    for ix in json.loads(body)["data"]:
        entity_id = f"ix:{ix['id']}"
        for key, metric in (("net_count", "networks_present"), ("fac_count", "facilities")):
            if ix.get(key) is not None:
                yield derive.Observation(entity_id=entity_id, metric=metric, value=int(ix[key]), unit="count")
        # Location carried as data so the capacity rows can be mapped without
        # a side lookup that would rot.
        for key, metric in (("name", "ix_name"), ("city", "city"), ("country", "country"),
                            ("region_continent", "continent")):
            if ix.get(key):
                yield derive.Observation(entity_id=entity_id, metric=metric, value=ix[key], unit="ref")


def parse_capacity(body: bytes, ctx: derive.ParseContext):
    ports = json.loads(body)["data"]
    per_net: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    per_pair: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])

    for port in ports:
        if not port.get("operational"):
            continue  # a configured-but-dark port is not capacity
        asn, ix_id = port["asn"], port["ix_id"]
        speed = int(port.get("speed") or 0)
        per_net[asn][0] += 1
        per_net[asn][1] += speed
        key = (asn, ix_id)
        per_pair[key][0] += 1
        per_pair[key][1] += speed

    for (asn, ix_id), (count, speed) in sorted(per_pair.items()):
        entity = f"net:{NETWORKS.get(asn, asn)}/ix:{ix_id}"
        yield derive.Observation(entity_id=entity, metric="declared_capacity", value=speed, unit="Mbps")
        yield derive.Observation(entity_id=entity, metric="ports", value=count, unit="count")

    for asn, (count, speed) in sorted(per_net.items()):
        entity = f"net:{NETWORKS.get(asn, asn)}"
        yield derive.Observation(entity_id=entity, metric="declared_capacity_total", value=speed, unit="Mbps")
        yield derive.Observation(entity_id=entity, metric="ports_total", value=count, unit="count")
        yield derive.Observation(entity_id=entity, metric="exchanges_present", value=len({k[1] for k in per_pair if k[0] == asn}), unit="count")


derive.register("pdb-exchanges.v1", parse_exchanges, PARSER_VERSION)
derive.register("pdb-capacity.v1", parse_capacity, PARSER_VERSION)


def parse_facilities(body: bytes, ctx: derive.ParseContext):
    """Facility coordinates, aggregated to the metro that owns them.

    Per-facility rows would be 5,800 mostly-static observations a week to
    support one join. The metro is the unit every other source keys on, so
    that is the unit stored: one point per (city, country), with the facility
    count and the mean position of the buildings in it.
    """
    by_metro: dict[tuple, list] = defaultdict(lambda: [0, 0.0, 0.0, 0])
    for fac in json.loads(body)["data"]:
        lat, lon = fac.get("latitude"), fac.get("longitude")
        if lat is None or lon is None:
            continue
        key = (fac.get("city") or "", fac.get("country") or "")
        slot = by_metro[key]
        slot[0] += 1
        slot[1] += float(lat)
        slot[2] += float(lon)
        slot[3] += int(fac.get("net_count") or 0)

    for (city, country), (count, lat_sum, lon_sum, nets) in sorted(by_metro.items()):
        if not city:
            continue
        entity = f"metro:{country}/{city}"
        yield derive.Observation(entity_id=entity, metric="facilities", value=count, unit="count")
        yield derive.Observation(entity_id=entity, metric="networks_at_facilities", value=nets, unit="count")
        yield derive.Observation(entity_id=entity, metric="latitude", value=round(lat_sum / count, 4), unit="deg")
        yield derive.Observation(entity_id=entity, metric="longitude", value=round(lon_sum / count, 4), unit="deg")


derive.register("pdb-facilities.v1", parse_facilities, PARSER_VERSION)
