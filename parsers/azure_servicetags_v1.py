"""azure.servicetags.v1 — Azure's published IP surface, tag by tag.

The file is Microsoft's firewall-configuration feed: every Azure service, in
every region, and the address prefixes it answers from. It is the Azure half of
the question this repo already asks of AWS -- which services reach which
regions, and in what order -- and it exists because AWS alone cannot separate
"this vendor is slow here" from "nobody has built this out yet" (Q10).

WHY IT PERISHES. `changeNumber` was 417 at first capture, so Microsoft has
published 417 versions of this file. Two are downloadable. The filename carries
a Monday's date and about a fortnight is retained -- 20260907 and 20260831
answered, 20260824 was already purged. The loss is countable, which is rarer
than the loss itself.

GRAIN. One entity per service tag, which is a (service, region) pair: 3,321
tags across 78 regions and 98 system services, 95% carrying both. The prefix
COUNT travels rather than the prefixes themselves -- 95,623 of them would be
half a million observations a month to answer a question nobody asked, and the
raw bytes are archived either way. What matters across captures is a tag
appearing, disappearing, or changing size.
"""

import json

from wss import derive

PARSER_VERSION = "1"


def parse(body: bytes, ctx: derive.ParseContext):
    doc = json.loads(body)

    # File-level, so a chart can say which vintage it is reading without
    # reopening the archive. changeNumber is Microsoft's own version counter
    # and is the measure of how much history is unpublished.
    change = doc.get("changeNumber")
    if change is not None:
        yield derive.Observation("feed:azure_servicetags", "change_number",
                                 int(change), "count")
    values = doc.get("values") or []
    yield derive.Observation("feed:azure_servicetags", "tags_total",
                             len(values), "count")

    regions, services, prefixes = set(), set(), 0
    for tag in values:
        name = (tag.get("name") or "").strip()
        props = tag.get("properties") or {}
        if not name:
            continue
        region = (props.get("region") or "").strip()
        service = (props.get("systemService") or "").strip()
        addrs = props.get("addressPrefixes") or []
        prefixes += len(addrs)
        if region:
            regions.add(region)
        if service:
            services.add(service)

        eid = f"tag:{name}"
        # The count, not the prefixes. 95,623 prefixes would be half a million
        # observations a month; the raw bytes hold them if anyone ever needs one.
        yield derive.Observation(eid, "prefix_count", len(addrs), "count")
        # v4 and v6 separately: a region gaining IPv6 is a different event from
        # one gaining capacity, and summing them hides it.
        v6 = sum(1 for a in addrs if ":" in str(a))
        yield derive.Observation(eid, "prefix_count_v6", v6, "count")
        if region:
            yield derive.Observation(eid, "region", region, "name")
        if service:
            yield derive.Observation(eid, "service", service, "name")
        cn = (tag.get("id") or "").strip()
        if cn and cn != name:
            yield derive.Observation(eid, "tag_id", cn, "name")

    yield derive.Observation("feed:azure_servicetags", "regions_total",
                             len(regions), "count")
    yield derive.Observation("feed:azure_servicetags", "services_total",
                             len(services), "count")
    yield derive.Observation("feed:azure_servicetags", "prefixes_total",
                             prefixes, "count")


derive.register("azure.servicetags.v1", parse, PARSER_VERSION)
