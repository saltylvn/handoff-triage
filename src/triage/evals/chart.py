"""python -m triage.evals.chart draws the threshold trade-off from the final eval as a plain SVG.
No plotting library: one small chart doesn't justify the dependency. Both measures are percentages,
so they share one axis."""

import json
from html import escape
from pathlib import Path

SERIES = (
    ("auto_precision", "Correct when acting alone", "#3987e5"),
    ("auto_rate", "Handled without a person", "#d55181"),
)
INK, MUTED, GRID, SURFACE = "#f5f1eb", "#aaa6a2", "#2e2e36", "#0a0a0e"
WIDTH, HEIGHT = 720, 420
LEFT, RIGHT, TOP, BOTTOM = 56, 190, 92, 56
MIN_LABEL_GAP = 18


def render(
    sweep: list[dict[str, float | int | None]],
    title: str,
    subtitle: str,
    chosen: float | None = None,
) -> str:
    thresholds = [float(row["threshold"] or 0) for row in sweep]
    low, high = min(thresholds), max(thresholds)

    def x(value: float) -> float:
        return LEFT + (value - low) / (high - low) * (WIDTH - LEFT - RIGHT)

    def y(fraction: float) -> float:
        return TOP + (1 - fraction) * (HEIGHT - TOP - BOTTOM)

    def text(px: float, py: float, words: str, size: int, fill: str, anchor: str = "start") -> str:
        return (
            f'<text x="{px:.1f}" y="{py:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}">{escape(words)}</text>'
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{escape(title)}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{SURFACE}"/>',
        text(LEFT, 30, title, 18, INK),
        text(LEFT, 52, subtitle, 13, MUTED),
    ]
    for tick in (0, 0.25, 0.5, 0.75, 1):
        parts.append(
            f'<line x1="{LEFT}" x2="{WIDTH - RIGHT}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" '
            f'stroke="{GRID}"/>'
        )
        parts.append(text(LEFT - 8, y(tick) + 4, f"{tick:.0%}", 12, MUTED, "end"))
    for mark in thresholds[::2] + ([high] if len(thresholds) % 2 == 0 else []):
        parts.append(text(x(mark), HEIGHT - BOTTOM + 20, f"{mark:.2f}", 12, MUTED, "middle"))
    parts.append(
        text((LEFT + WIDTH - RIGHT) / 2, HEIGHT - 12, "Confidence threshold", 13, MUTED, "middle")
    )

    if chosen is not None:
        parts.append(
            f'<line x1="{x(chosen):.1f}" x2="{x(chosen):.1f}" y1="{TOP}" '
            f'y2="{HEIGHT - BOTTOM}" stroke="{MUTED}"/>'
        )
        parts.append(text(x(chosen), TOP - 6, f"chosen: {chosen:.2f}", 12, INK, "middle"))

    ends: dict[str, float] = {}
    legend_x = float(LEFT)
    for key, label, color in SERIES:
        points = [(float(r["threshold"] or 0), r[key]) for r in sweep if r[key] is not None]
        path = " ".join(f"{x(t):.1f},{y(float(v or 0)):.1f}" for t, v in points)
        parts.append(
            f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for threshold, value in points:
            parts.append(
                f'<circle cx="{x(threshold):.1f}" cy="{y(float(value or 0)):.1f}" r="4" '
                f'fill="{color}" stroke="{SURFACE}" stroke-width="2"><title>{escape(label)} at '
                f"{threshold:.2f}: {float(value or 0):.0%}</title></circle>"
            )
        ends[key] = float(points[-1][1] or 0)
        parts.append(f'<circle cx="{legend_x + 5:.1f}" cy="68" r="5" fill="{color}"/>')
        parts.append(text(legend_x + 15, 72, label, 13, INK))
        legend_x += 15 + len(label) * 7.0 + 24

    gap = abs(y(ends["auto_precision"]) - y(ends["auto_rate"]))
    if gap >= MIN_LABEL_GAP:  # when the lines meet, the legend and README table carry the values
        for key, label, _ in SERIES:
            first_word = label.split()[0]
            parts.append(
                text(WIDTH - RIGHT + 10, y(ends[key]) + 4, f"{ends[key]:.0%} {first_word}", 13, INK)
            )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    report = json.loads(Path("eval/results/summary-all.json").read_text())
    test = report["test"]
    svg = render(
        test["threshold_sweep"],
        "A higher threshold automates less and is slightly more accurate",
        f"{test['items']} held-out synthetic messages, {report['model']}",
        report["threshold_chosen_on_dev"],
    )
    Path("docs/assets/threshold-tradeoff.svg").write_text(svg)


if __name__ == "__main__":
    main()
