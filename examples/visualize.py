#!/usr/bin/env python3
"""Render charts from derived/observations/*.csv as SVG.

    python examples/visualize.py

Two charts, written to examples/charts/:

  region-maturity.svg   services available per AWS region, ranked — what you
                        give up by deploying somewhere other than us-east-1
  rollout-frontier.svg  the services in the fewest regions — where AWS is
                        currently expanding, and what has stalled
  region-gap.svg        what a newly opened region still lacks, and how much
                        of the catalogue ships as the "opening kit"
  network-strategy.svg  breadth against depth of interconnection — who is
                        everywhere-and-thin, who is concentrated-and-deep
  capacity-history.svg  declared capacity per network over time. Renders a
                        placeholder until enough captures exist; this repo is
                        longitudinal, and the chart should say so from day one

Both read the derived table, never the raw archive. Stdlib only,
deterministic output: the same observations always produce the same bytes.
"""

from __future__ import annotations

import argparse
import csv
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


NET_COLOUR = {"akamai": "#2a78d6", "meta": "#eb6834", "aws": "#1baf7a", "cloudflare": "#4a3aa7"}
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
    left, right, top, bottom = 70.0, 150.0, 104.0, 58.0
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
        colour = NET_COLOUR.get(name, NET_OTHER)
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
            body.append(f'<circle cx="{left + 30}" cy="{y - 4}" r="5" fill="{NET_COLOUR.get(n, NET_OTHER)}"/>')
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
            body.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{NET_COLOUR.get(n, NET_OTHER)}" stroke-width="2" stroke-linejoin="round"/>')
            x, y = pts[-1]
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{NET_COLOUR.get(n, NET_OTHER)}" stroke="{SURFACE}" stroke-width="2"/>')
            body.append(svg_text(x + 10, y + 3.5, f"{n} {series[n][dates[-1]]/1e6:.1f}T", size=11, fill=INK, weight="600"))
        body.append(f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="{BASELINE}" stroke-width="1"/>')
    body.append(svg_text(24, height - 8, "source: wss-cloud-footprint · peeringdb.networks.capacity · declared capacity, not measured traffic", size=10, fill=MUTED))
    out.write_text(wrap(width, height, "Declared capacity over time",
                        "Line chart of declared interconnection capacity per network across weekly captures.", "\n".join(body)), encoding="utf-8")
    return f"{out.relative_to(REPO)} — {len(dates)} capture(s)" + ("" if len(dates) >= needed else f", placeholder until {needed}")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    regions, as_of = load("services_available")
    if not regions:
        print("no observations yet — run capture + derive first")
        return 1
    total_services = max(v for _, v in regions)
    thin = sum(1 for _, v in regions if v < total_services * 0.7)
    print(
        ranked_bars(
            regions,
            OUT_DIR / "region-maturity.svg",
            title="AWS region maturity",
            subtitle=(
                f"services available per region · {len(regions)} regions · snapshot {as_of} · "
                f"darker = below 70% of full coverage ({thin} regions)"
            ),
            caption="source: wss-cloud-footprint · aws.services.regional · CC-BY-4.0",
            desc="Ranked bar chart of the number of AWS services available in each region.",
            highlight=thin,
        )
    )

    services, _ = load("regions_available")
    frontier = sorted(
        [(s, v) for s, v in services if v < len(regions)], key=lambda kv: (kv[1], kv[0])
    )[:20]
    universal = sum(1 for _, v in services if v == len(regions))
    print(region_gap(OUT_DIR / "region-gap.svg"))
    print(network_strategy(OUT_DIR / "network-strategy.svg"))
    print(capacity_history(OUT_DIR / "capacity-history.svg"))
    print(
        ranked_bars(
            frontier,
            OUT_DIR / "rollout-frontier.svg",
            title="The rollout frontier",
            subtitle=(
                f"the 20 least-distributed AWS services · "
                f"{universal} of {len(services)} services are already in all {len(regions)} regions"
            ),
            caption="source: wss-cloud-footprint · aws.services.regional · CC-BY-4.0",
            desc="Ranked bar chart of AWS services present in the fewest regions.",
            axis_max=len(regions),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
