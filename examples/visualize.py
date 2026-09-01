#!/usr/bin/env python3
"""Render charts from derived/observations/*.csv as SVG.

    python examples/visualize.py

Two charts, written to examples/charts/:

  region-maturity.svg   services available per AWS region, ranked — what you
                        give up by deploying somewhere other than us-east-1
  rollout-frontier.svg  the services in the fewest regions — where AWS is
                        currently expanding, and what has stalled

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
