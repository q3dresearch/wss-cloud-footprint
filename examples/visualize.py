#!/usr/bin/env python3
"""Render charts from derived/observations/*.csv as SVG.

    python examples/visualize.py

Two charts, written to examples/charts/:

  rollout-frontier.svg  the services in the fewest regions — where AWS is
                        currently expanding, and what has stalled
  region-gap.svg        what a newly opened region still lacks, and how much
                        of the catalogue ships as the "opening kit"
  network-strategy.svg  breadth against depth of interconnection — who is
                        everywhere-and-thin, who is concentrated-and-deep
  metro-concentration.svg  is a metro shared by everyone or owned by one
                        network — saturation against territorial dominance
  capacity-history.svg  declared capacity per network over time. Renders a
                        placeholder until enough captures exist; this repo is
                        longitudinal, and the chart should say so from day one

Both read the derived table, never the raw archive. Stdlib only,
deterministic output: the same observations always produce the same bytes.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "examples" / "charts"

# Validated reference palette; magnitude is a single-hue sequential job, so
# one blue does all the work and text stays in ink tokens.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
HUE = "#2a78d6"
HUE_SOFT = "#9ec5f4"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def load(metric: str) -> tuple[list[tuple[str, int]], str]:
    """Latest observation per entity for one metric, plus its date."""
    rows = []
    for partition in sorted((REPO / "derived" / "observations").glob("*.csv")):
        with partition.open(encoding="utf-8", newline="") as fh:
            rows.extend(r for r in csv.DictReader(fh) if r["metric"] == metric)
    if not rows:
        return [], ""
    latest = max(r["observed_at"] for r in rows)
    return (
        sorted(
            ((r["entity_id"].split(":", 1)[1], int(r["value"])) for r in rows if r["observed_at"] == latest),
            key=lambda kv: (-kv[1], kv[0]),
        ),
        latest[:10],
    )


def svg_text(x, y, text, *, size, fill, anchor="start", weight="normal", tabular=False) -> str:
    style = "font-variant-numeric: tabular-nums;" if tabular else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family=\'{FONT}\' font-size="{size}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" style="{style}">{escape(text)}</text>'
    )


def bar(x, y, w, h, colour=HUE, r=4) -> str:
    """Square at the baseline, 4px rounded data-end."""
    r = min(r, max(w / 2, 0.1), h / 2)
    return (
        f'<path d="M{x:.1f},{y:.1f} h{w - r:.1f} q{r},0 {r},{r} v{h - 2 * r:.1f} '
        f'q0,{r} -{r},{r} h-{w - r:.1f} z" fill="{colour}"/>'
    )


def legend(items, y: float, x0: float = 24.0) -> list[str]:
    """A legend is always present when more than one colour carries meaning."""
    out, x = [], x0
    for label, colour in items:
        out.append(f'<rect x="{x:.1f}" y="{y - 9:.1f}" width="10" height="10" rx="2" fill="{colour}"/>')
        out.append(svg_text(x + 16, y, label, size=11, fill=INK2))
        x += 16 + len(label) * 6.6 + 18
    return out


def wrap(width, height, title, desc, body) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">\n'
        f"<title>{escape(title)}</title>\n<desc>{escape(desc)}</desc>\n"
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>\n{body}\n</svg>\n'
    )


def ranked_bars(
    data: list[tuple[str, int]],
    out: Path,
    *,
    title: str,
    subtitle: str,
    caption: str,
    desc: str,
    highlight: int = 0,
    axis_max: int | None = None,
) -> str:
    width, left, right, top = 900.0, 210.0, 96.0, 74.0
    bar_h, gap = 14.0, 6.0
    height = top + len(data) * (bar_h + gap) + 34
    vmax = axis_max or max(v for _, v in data)
    span = width - left - right

    body = [
        svg_text(24, 30, title, size=16, fill=INK, weight="600"),
        svg_text(24, 50, subtitle, size=12, fill=INK2),
    ]
    # recessive gridlines at clean intervals, drawn behind the bars
    step = 50 if vmax > 120 else 10
    tick = 0
    while tick <= vmax:
        gx = left + tick / vmax * span
        body.append(f'<line x1="{gx:.1f}" y1="{top - 8}" x2="{gx:.1f}" y2="{height - 30}" stroke="{GRID}" stroke-width="1"/>')
        body.append(svg_text(gx, height - 16, str(tick), size=10, fill=MUTED, anchor="middle", tabular=True))
        tick += step
    body.append(f'<line x1="{left}" y1="{top - 8}" x2="{left}" y2="{height - 30}" stroke="{BASELINE}" stroke-width="1"/>')

    for i, (label, value) in enumerate(data):
        y = top + i * (bar_h + gap)
        w = max(1.5, value / vmax * span)
        # the highlighted tail is the story; the rest is context
        colour = HUE if (not highlight or i >= len(data) - highlight) else HUE_SOFT
        body.append(bar(left, y, w, bar_h, colour))
        name = label if len(label) <= 34 else label[:33].rstrip(" (") + "…"
        body.append(svg_text(left - 10, y + bar_h - 3, name, size=11, fill=INK2, anchor="end"))
        body.append(svg_text(left + w + 7, y + bar_h - 3, str(value), size=11, fill=INK, weight="600", tabular=True))

    body.append(svg_text(24, height - 4, caption, size=10, fill=MUTED))
    out.write_text(wrap(width, height, title, desc, "\n".join(body)), encoding="utf-8")
    return f"{out.relative_to(REPO)} — {len(data)} bars"


def membership(root: Path = REPO):
    """region -> set of services, straight from the derived table."""
    from collections import defaultdict
    member = defaultdict(set)
    for partition in sorted((root / "derived" / "observations").glob("*.csv")):
        with partition.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["metric"] == "available":
                    region, service = r["entity_id"][7:].split("/service:", 1)
                    member[region].add(service)
    return member


def region_gap(out: Path, thinnest: int = 4) -> str:
    """What the newest regions still lack, and what always ships first."""
    member = membership()
    if not member:
        return "region-gap.svg skipped: no membership observations yet"
    order = sorted(member, key=lambda r: len(member[r]))
    thin, fat = order[:thinnest], order[-1]
    kit = set.intersection(*[member[r] for r in thin])
    universe = member[fat]

    data = [(r, len(kit), len(member[r]) - len(kit), len(universe) - len(member[r])) for r in reversed(order)]
    width, left, right, top_pad = 900.0, 168.0, 150.0, 116.0
    bar_h, gap = 13.0, 5.0
    height = top_pad + len(data) * (bar_h + gap) + 40
    span = width - left - right
    total = len(universe)

    body = [
        svg_text(24, 30, "What a new region still lacks", size=16, fill=INK, weight="600"),
        svg_text(24, 50, f"every AWS region against the {total}-service catalogue of {fat}", size=12, fill=INK2),
        svg_text(24, 70, f"the opening kit — {len(kit)} services present in all {thinnest} newest regions — is what AWS treats as the minimum viable region", size=11, fill=MUTED),
    ]
    body += legend([("opening kit", HUE), ("added since", HUE_SOFT), ("still missing", "#e8e7e1")], 96)
    for i, (region, k, extra, missing) in enumerate(data):
        y = top_pad + i * (bar_h + gap)
        x = left
        for value, colour in ((k, HUE), (extra, HUE_SOFT), (missing, "#e8e7e1")):
            w = value / total * span
            if w > 0.5:
                body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(0.5, w - 2):.1f}" height="{bar_h}" fill="{colour}"/>')
            x += w
        body.append(svg_text(left - 10, y + bar_h - 3, region, size=10, fill=INK2 if region not in thin else INK, anchor="end", weight="600" if region in thin else "normal"))
        body.append(svg_text(width - right + 8, y + bar_h - 3, f"{k + extra} of {total}" + ("   ← newest" if region in thin else ""), size=10, fill=MUTED, tabular=True))
    body.append(svg_text(24, height - 8, "source: wss-cloud-footprint · aws.services.regional · CC-BY-4.0", size=10, fill=MUTED))
    out.write_text(wrap(width, height, "What a new region still lacks",
                        "Stacked bar per AWS region showing the opening-kit services, services added since, and services still missing.", "\n".join(body)), encoding="utf-8")
    return f"{out.relative_to(REPO)} — {len(data)} regions, opening kit {len(kit)} services"


# Colour carries the network's *kind*, not its identity — identity is already
# on every bubble as a direct label, so spending colour on it would be waste.
# Three classes, which is also the all-pairs colour-vision limit.
NET_KIND = {
    "aws": "cloud", "google": "cloud", "microsoft": "cloud",
    "oracle": "cloud", "digitalocean": "cloud",
    "cloudflare": "cdn", "fastly": "cdn", "akamai": "cdn",
    "meta": "content",
}
KIND_COLOUR = {"cloud": "#2a78d6", "cdn": "#eb6834", "content": "#1baf7a"}
KIND_LABEL = {"cloud": "enterprise cloud", "cdn": "CDN / edge", "content": "content network"}
NET_OTHER = "#b8b7b0"


def capacity_rows():
    """(date, network, Mbps) for every capture we hold."""
    out = []
    for partition in sorted((REPO / "derived" / "observations").glob("*.csv")):
        with partition.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["metric"] == "declared_capacity_total":
                    out.append((r["observed_at"][:10], r["entity_id"][4:], int(r["value"])))
    return out


def network_strategy(out: Path) -> str:
    """Breadth (exchanges reached) against depth (capacity per exchange).

    Same total capacity can be spread thin across many exchanges or
    concentrated in few — a strategy difference invisible in a ranking.
    """
    rows_ = []
    for partition in sorted((REPO / "derived" / "observations").glob("*.csv")):
        with partition.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["metric"] in ("declared_capacity_total", "exchanges_present"):
                    rows_.append(r)
    if not rows_:
        return "network-strategy.svg skipped: no capacity observations yet"
    latest = max(r["observed_at"] for r in rows_)
    cap, exch = {}, {}
    for r in rows_:
        if r["observed_at"] != latest:
            continue
        (cap if r["metric"] == "declared_capacity_total" else exch)[r["entity_id"][4:]] = int(r["value"])
    pts = [(n, exch[n], cap[n] / exch[n] / 1000, cap[n] / 1e6) for n in cap if exch.get(n)]

    width, height = 900.0, 470.0
    left, right, top, bottom = 70.0, 150.0, 122.0, 58.0
    xmax = max(p[1] for p in pts) * 1.12
    ymax = max(p[2] for p in pts) * 1.15
    vmax = max(p[3] for p in pts)
    x_of = lambda v: left + v / xmax * (width - left - right)  # noqa: E731
    y_of = lambda v: (height - bottom) - v / ymax * (height - bottom - top)  # noqa: E731

    body = [
        svg_text(24, 30, "Two ways to build a network", size=16, fill=INK, weight="600"),
        svg_text(24, 50, f"exchanges reached against average capacity at each · snapshot {latest[:10]}", size=12, fill=INK2),
        svg_text(24, 70, "right = present in more places · up = heavier at each one · bubble area = total declared capacity", size=11, fill=MUTED),
    ]
    body += legend([(KIND_LABEL[k], KIND_COLOUR[k]) for k in ("cloud", "cdn", "content")], 94)
    for v in range(0, int(xmax), 100):
        if v:
            gx = x_of(v)
            body.append(f'<line x1="{gx:.1f}" y1="{top - 8}" x2="{gx:.1f}" y2="{height - bottom}" stroke="{GRID}" stroke-width="1"/>')
            body.append(svg_text(gx, height - bottom + 18, str(v), size=10, fill=MUTED, anchor="middle", tabular=True))
    for v in range(0, int(ymax), 100):
        if v:
            gy = y_of(v)
            body.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{width - right}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
            body.append(svg_text(left - 8, gy + 3.5, str(v), size=10, fill=MUTED, anchor="end", tabular=True))
    body.append(svg_text(left - 8, top - 14, "Gbps per exchange", size=10, fill=MUTED, anchor="start"))
    body.append(svg_text((left + width - right) / 2, height - 14, "internet exchanges present at", size=10, fill=MUTED, anchor="middle"))
    body.append(f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="{BASELINE}" stroke-width="1"/>')

    placed: list[tuple[float, float, float]] = []
    for name, breadth, depth, total in sorted(pts, key=lambda p: -p[3]):
        x, y = x_of(breadth), y_of(depth)
        r = 5 + 16 * (total / vmax) ** 0.5
        colour = KIND_COLOUR.get(NET_KIND.get(name), NET_OTHER)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{colour}" fill-opacity="0.55" stroke="{SURFACE}" stroke-width="2"/>')
        label = f"{name} {total:.0f}T"
        half = len(label) * 2.9
        ly = y - r - 6
        # lift the label until it clears every one already placed
        while any(abs(ly - py) < 12 and not (x + half < px - pw or x - half > px + pw) for px, pw, py in placed):
            ly -= 12
        placed.append((x, half, ly))
        body.append(svg_text(x, ly, label, size=10, fill=INK2, anchor="middle", weight="600"))
    body.append(svg_text(24, height - 4, "source: wss-cloud-footprint · peeringdb.networks.capacity · declared capacity, not measured traffic", size=10, fill=MUTED))
    out.write_text(wrap(width, height, "Two ways to build a network",
                        "Scatter of internet exchanges present at against average declared capacity per exchange, bubble area total capacity.", "\n".join(body)), encoding="utf-8")
    return f"{out.relative_to(REPO)} — {len(pts)} networks"


def metro_capacity():
    """(metro -> {network: Mbps}) using the exchange's city as the key."""
    rows_ = []
    for partition in sorted((REPO / "derived" / "observations").glob("*.csv")):
        with partition.open(encoding="utf-8", newline="") as fh:
            rows_.extend(csv.DictReader(fh))
    latest = max((r["observed_at"] for r in rows_ if r["metric"] == "declared_capacity"), default=None)
    if not latest:
        return {}
    city = {r["entity_id"]: r["value"] for r in rows_ if r["metric"] == "city"}
    per = defaultdict(lambda: defaultdict(int))
    for r in rows_:
        if r["metric"] == "declared_capacity" and r["observed_at"] == latest:
            net, ix = r["entity_id"][4:].split("/ix:", 1)
            metro = city.get(f"ix:{ix}")
            if metro:
                per[metro][net] += int(r["value"])
    return per


def metro_concentration(out: Path, floor_tbps: float = 1.0) -> str:
    """Shared or owned? The largest network's share, against metro size.

    Left means many networks split the metro; right means one holds most of
    it. The practical question behind it: a disaster-recovery metro served
    by a single network is not multi-cloud, whatever the contract says.
    """
    import math
    per = metro_capacity()
    pts = []
    for metro, nets in per.items():
        total = sum(nets.values())
        if total < floor_tbps * 1e6:
            continue
        leader, lead = max(nets.items(), key=lambda kv: kv[1])
        pts.append((metro, total / 1e6, lead / total, len(nets), leader))
    if len(pts) < 5:
        return "metro-concentration.svg skipped: too few metros yet"

    width, height = 920.0, 500.0
    left, right, top, bottom = 74.0, 44.0, 116.0, 58.0
    xmin, xmax = min(p[2] for p in pts) * 0.95, max(p[2] for p in pts) * 1.04
    ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts) * 1.2
    x_of = lambda v: left + (v - xmin) / (xmax - xmin) * (width - left - right)
    y_of = lambda v: (height - bottom) - (math.log10(v) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin)) * (height - bottom - top)

    body = [
        svg_text(24, 30, "Shared, or owned?", size=16, fill=INK, weight="600"),
        svg_text(24, 50, f"{len(pts)} metros above {floor_tbps:g} Tbps \u00b7 horizontal = the largest network's share of that metro", size=12, fill=INK2),
        svg_text(24, 70, "left = many networks split it \u00b7 right = one network holds most of it \u00b7 colour = kind of network leading", size=11, fill=MUTED),
    ]
    kinds = sorted({NET_KIND.get(p[4], "other") for p in pts})
    body += legend([(KIND_LABEL.get(k, k), KIND_COLOUR.get(k, NET_OTHER)) for k in kinds], 94)
    for frac in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
        if xmin <= frac <= xmax:
            gx = x_of(frac)
            body.append(f'<line x1="{gx:.1f}" y1="{top - 8}" x2="{gx:.1f}" y2="{height - bottom}" stroke="{GRID}" stroke-width="1"/>')
            body.append(svg_text(gx, height - bottom + 18, f"{frac * 100:.0f}%", size=10, fill=MUTED, anchor="middle", tabular=True))
    for v in (1, 2, 5, 10, 20):
        if ymin <= v <= ymax:
            gy = y_of(v)
            body.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{width - right}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
            body.append(svg_text(left - 8, gy + 3.5, f"{v}T", size=10, fill=MUTED, anchor="end", tabular=True))
    body.append(svg_text(left - 8, top - 14, "metro capacity", size=10, fill=MUTED, anchor="start"))
    body.append(svg_text((left + width - right) / 2, height - 14, "largest network's share of the metro  \u2192  more concentrated", size=10, fill=MUTED, anchor="middle"))
    body.append(f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="{BASELINE}" stroke-width="1"/>')

    placed = []
    for metro, total, share, nets, leader in sorted(pts, key=lambda p: -p[1]):
        x, y = x_of(share), y_of(total)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{KIND_COLOUR.get(NET_KIND.get(leader), NET_OTHER)}" fill-opacity="0.8" stroke="{SURFACE}" stroke-width="2"/>')
        if len(placed) < 12:
            label = metro.split("/")[0]
            w = len(label) * 6.4 + 6
            if x + 9 + w > width - right:
                lx, anchor, x0, x1 = x - 9, "end", x - 9 - w, x - 9
            else:
                lx, anchor, x0, x1 = x + 9, "start", x + 9, x + 9 + w
            if any(abs(y - py) < 12 and not (x1 < bx0 or x0 > bx1) for bx0, bx1, py in placed):
                continue
            body.append(svg_text(lx, y + 3.5, label, size=10, fill=INK2, anchor=anchor))
            placed.append((x0, x1, y))
    body.append(svg_text(24, height - 4, "source: wss-cloud-footprint \u00b7 peeringdb \u00b7 declared capacity, not measured traffic", size=10, fill=MUTED))
    out.write_text(wrap(width, height, "Shared, or owned?",
                        "Scatter of metro total declared capacity against the largest network's share of that metro.", "\n".join(body)), encoding="utf-8")
    return f"{out.relative_to(REPO)} \u2014 {len(pts)} metros"


def capacity_history(out: Path, needed: int = 4) -> str:
    """Declared capacity over time — or an honest placeholder until it exists.

    The repo is longitudinal; the chart should advertise that on day one
    rather than appearing months later, so it renders either way.
    """
    data = capacity_rows()
    if not data:
        return "capacity-history.svg skipped: no capacity observations yet"
    dates = sorted({d for d, _, _ in data})
    series = {}
    for d, n, v in data:
        series.setdefault(n, {})[d] = v
    top = sorted(series, key=lambda n: -max(series[n].values()))[:4]

    width, height = 900.0, 420.0
    left, right, top_pad, bottom = 70.0, 168.0, 104.0, 56.0
    vmax = max(v for _, _, v in data) / 1e6 * 1.15
    body = [
        svg_text(24, 30, "Declared capacity over time", size=16, fill=INK, weight="600"),
        svg_text(24, 50, f"Tbps per network, one point per weekly capture · {len(dates)} capture(s) so far", size=12, fill=INK2),
    ]
    if len(dates) < needed:
        body.append(svg_text(24, 70, f"Not a chart yet — it needs {needed - len(dates)} more weekly capture(s).", size=11, fill=MUTED))
        body.append(f'<rect x="{left}" y="{top_pad}" width="{width - left - right:.1f}" height="{height - top_pad - bottom:.1f}" fill="#f4f4f0" rx="6"/>')
        msg = [
            "Nobody publishes this history — not AWS, not PeeringDB.",
            "There is no window to page back through and no archive to import.",
            f"The series starts on {dates[0]} because that is the day capture started.",
            "",
            "Today's values, which become the first point:",
        ]
        for i, line in enumerate(msg):
            body.append(svg_text(left + 24, top_pad + 34 + i * 19, line, size=12, fill=INK2 if i < 3 else INK2, weight="normal"))
        for i, n in enumerate(top):
            v = max(series[n].values()) / 1e6
            y = top_pad + 34 + (len(msg) + i) * 19
            body.append(f'<circle cx="{left + 30}" cy="{y - 4}" r="5" fill="{KIND_COLOUR.get(NET_KIND.get(n), NET_OTHER)}"/>')
            body.append(svg_text(left + 44, y, f"{n} — {v:.1f} Tbps", size=12, fill=INK, weight="600"))
    else:
        d0, d1 = dates[0], dates[-1]
        import datetime as _dt
        o0, o1 = _dt.date.fromisoformat(d0).toordinal(), _dt.date.fromisoformat(d1).toordinal()
        x_of = lambda d: left + (_dt.date.fromisoformat(d).toordinal() - o0) / max(1, o1 - o0) * (width - left - right)  # noqa: E731
        y_of = lambda v: (height - bottom) - v / vmax * (height - bottom - top_pad)  # noqa: E731
        for tick in range(0, int(vmax) + 20, 20):
            gy = y_of(tick)
            body.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{width - right}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
            body.append(svg_text(left - 8, gy + 3.5, str(tick), size=10, fill=MUTED, anchor="end", tabular=True))
        for n in top:
            pts = [(x_of(d), y_of(series[n][d] / 1e6)) for d in sorted(series[n])]
            body.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{KIND_COLOUR.get(NET_KIND.get(n), NET_OTHER)}" stroke-width="2" stroke-linejoin="round"/>')
            x, y = pts[-1]
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{KIND_COLOUR.get(NET_KIND.get(n), NET_OTHER)}" stroke="{SURFACE}" stroke-width="2"/>')
            body.append(svg_text(x + 10, y + 3.5, f"{n} {series[n][dates[-1]]/1e6:.1f}T", size=11, fill=INK, weight="600"))
        body.append(f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="{BASELINE}" stroke-width="1"/>')
    body.append(svg_text(24, height - 8, "source: wss-cloud-footprint · peeringdb.networks.capacity · declared capacity, not measured traffic", size=10, fill=MUTED))
    out.write_text(wrap(width, height, "Declared capacity over time",
                        "Line chart of declared interconnection capacity per network across weekly captures.", "\n".join(body)), encoding="utf-8")
    return f"{out.relative_to(REPO)} — {len(dates)} capture(s)" + ("" if len(dates) >= needed else f", placeholder until {needed}")


def rollout_frontier(out: Path, frontier, n_regions: int, universal: int, n_services: int) -> str:
    """Services in the fewest regions — and, for the thinnest, exactly where.

    A bare count answers "how far has this spread" but not the question that
    follows immediately: spread *where*? For anything in six regions or
    fewer the regions are named outright, because at that size the list is
    the finding.
    """
    member = membership()
    where = defaultdict(list)
    for region, services in member.items():
        for s in services:
            where[s].append(region)

    width, left, right, top = 940.0, 250.0, 300.0, 92.0
    bar_h, gap = 14.0, 6.0
    height = top + len(frontier) * (bar_h + gap) + 40
    span = width - left - right
    body = [
        svg_text(24, 30, "The rollout frontier", size=16, fill=INK, weight="600"),
        svg_text(24, 50, f"the {len(frontier)} least-distributed AWS services, by how many of {n_regions} regions carry them", size=12, fill=INK2),
        svg_text(24, 70, f"for context, {universal} of {n_services} services are already in every region — these are the ones still moving, or stalled", size=11, fill=MUTED),
    ]
    for tick in range(0, n_regions + 1, 5):
        gx = left + tick / n_regions * span
        body.append(f'<line x1="{gx:.1f}" y1="{top - 8}" x2="{gx:.1f}" y2="{height - 34}" stroke="{GRID}" stroke-width="1"/>')
        body.append(svg_text(gx, height - 20, str(tick), size=10, fill=MUTED, anchor="middle", tabular=True))
    body.append(f'<line x1="{left}" y1="{top - 8}" x2="{left}" y2="{height - 34}" stroke="{BASELINE}" stroke-width="1"/>')
    for i, (name, count) in enumerate(frontier):
        y = top + i * (bar_h + gap)
        w = max(1.5, count / n_regions * span)
        body.append(bar(left, y, w, bar_h, HUE))
        label = name if len(name) <= 32 else name[:31].rstrip(" (") + "…"
        body.append(svg_text(left - 10, y + bar_h - 3, label, size=11, fill=INK2, anchor="end"))
        regions = sorted(where.get(name, []))
        detail = ", ".join(regions) if 0 < len(regions) <= 6 else f"{count} regions"
        body.append(svg_text(left + w + 7, y + bar_h - 3, detail[:52], size=10, fill=INK if len(regions) <= 6 else MUTED, tabular=True))
    body.append(svg_text(24, height - 6, "source: wss-cloud-footprint · aws.services.regional · CC-BY-4.0", size=10, fill=MUTED))
    out.write_text(wrap(width, height, "The rollout frontier",
                        "Ranked bar chart of AWS services present in the fewest regions, naming the regions for the thinnest.", "\n".join(body)), encoding="utf-8")
    return f"{out.relative_to(REPO)} — {len(frontier)} services"


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    regions, as_of = load("services_available")
    if not regions:
        print("no observations yet — run capture + derive first")
        return 1

    services, _ = load("regions_available")
    frontier = sorted(
        [(s, v) for s, v in services if v < len(regions)], key=lambda kv: (kv[1], kv[0])
    )[:20]
    universal = sum(1 for _, v in services if v == len(regions))
    print(region_gap(OUT_DIR / "region-gap.svg"))
    print(network_strategy(OUT_DIR / "network-strategy.svg"))
    print(metro_concentration(OUT_DIR / "metro-concentration.svg"))
    print(capacity_history(OUT_DIR / "capacity-history.svg"))
    print(rollout_frontier(OUT_DIR / "rollout-frontier.svg", frontier, len(regions), universal, len(services)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
