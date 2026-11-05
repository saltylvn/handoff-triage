"""Draws the README visuals as plain SVG: one idea per image, in plain words.

The look: near-black canvas, warm cream text, one rose accent, hairline cards with connector dots
and curved wires. Positions are explicit because automatic layout made these too busy to read."""

from html import escape
from itertools import pairwise
from pathlib import Path

BG, DOT, CARD, HAIRLINE = "#0a0a0e", "#1b1b21", "#131318", "#2e2e36"
INK, MUTED, LINE = "#f5f1eb", "#aaa6a2", "#6e6e78"
ROSE, ON_ROSE = "#e879a3", "#0a0a0e"
SANS = "ui-sans-serif, -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, Menlo, Consolas, monospace"
WIDTH = 1170
NODE_W, NODE_H = 180, 92

Point = tuple[float, float]


class Canvas:
    def __init__(self, height: int, eyebrow: str, headline: str, caption: str, label: str) -> None:
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(label)}">',
            '<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
            f'<circle cx="2" cy="2" r="1.1" fill="{DOT}"/></pattern>',
            *(
                f'<marker id="{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" '
                f'markerHeight="6.5" orient="auto-start-reverse"><path d="M1 1L9 5L1 9" '
                f'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
                'stroke-linejoin="round"/></marker>'
                for name, color in (("grey", LINE), ("rose", ROSE))
            ),
            "</defs>",
            f'<rect width="{WIDTH}" height="{height}" fill="{BG}"/>',
            f'<rect width="{WIDTH}" height="{height}" fill="url(#dots)"/>',
        ]
        self.parts.append(f'<circle cx="44" cy="51" r="3.5" fill="{ROSE}"/>')
        self.text(58, 56, eyebrow.upper(), 13, MUTED, MONO, letter_spacing="2")
        self.text(40, 104, headline, 36, INK, SANS, font_weight="600", letter_spacing="-0.8")
        self.text(
            WIDTH - 40,
            height - 24,
            caption,
            12,
            MUTED,
            MONO,
            text_anchor="end",
            letter_spacing="0.4",
        )

    def text(
        self, x: float, y: float, words: str, size: int, fill: str, font: str = SANS, **extra: str
    ) -> None:
        attrs = "".join(f' {key.replace("_", "-")}="{value}"' for key, value in extra.items())
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}"{attrs}>'
            f"{escape(words)}</text>"
        )

    def node(
        self,
        x: float,
        y: float,
        title: str,
        detail: str = "",
        rose: bool = False,
        w: int = NODE_W,
        h: int = NODE_H,
    ) -> None:
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
            f'fill="{ROSE if rose else CARD}" stroke="{ROSE if rose else HAIRLINE}" '
            'stroke-width="1.5"/>'
        )
        title_y = y + h / 2 - (3 if detail else -6)
        self.text(
            x + 18,
            title_y,
            title,
            18,
            ON_ROSE if rose else INK,
            SANS,
            font_weight="600",
            letter_spacing="-0.2",
        )
        if detail:
            self.text(x + 18, title_y + 23, detail, 14, ON_ROSE if rose else MUTED)

    def wire(self, start: Point, end: Point, rose: bool = False, both: bool = False) -> None:
        """A horizontal S-curve, like a wire between workflow nodes."""
        (x1, y1), (x2, y2) = start, end
        bend = max(abs(x2 - x1) * 0.5, 24)
        self.path(f"M {x1} {y1} C {x1 + bend} {y1}, {x2 - bend} {y2}, {x2} {y2}", rose, both)

    def path(self, d: str, rose: bool = False, both: bool = False) -> None:
        marker = "url(#rose)" if rose else "url(#grey)"
        start = f' marker-start="{marker}"' if both else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{ROSE if rose else LINE}" stroke-width="1.8" '
            f'stroke-linecap="round" marker-end="{marker}"{start}/>'
        )

    def ports(self, *points: Point) -> None:
        for x, y in points:
            self.parts.append(
                f'<circle cx="{x}" cy="{y}" r="4" fill="{BG}" stroke="{LINE}" stroke-width="1.6"/>'
            )

    def pill(self, x: float, y: float, words: str) -> None:
        width = len(words) * 7.2 + 24
        self.parts.append(
            f'<rect x="{x - width / 2}" y="{y - 13}" width="{width}" height="26" rx="13" '
            f'fill="{BG}" stroke="{HAIRLINE}"/>'
        )
        self.text(x, y + 4.5, words, 13, INK, SANS, text_anchor="middle")

    def save(self, name: str) -> None:
        self.parts.append("</svg>")
        Path(f"docs/assets/{name}.svg").write_text("\n".join(self.parts) + "\n")
        print(f"{name} {WIDTH},{self.height}")


def right(x: float, y: float, h: int = NODE_H, w: int = NODE_W) -> Point:
    return (x + w, y + h / 2)


def left(x: float, y: float, h: int = NODE_H) -> Point:
    return (x, y + h / 2)


def flow() -> None:
    c = Canvas(
        470,
        "How it works",
        "Automates the routine. Asks a person about the rest.",
        "fig. 01 — the workflow",
        "A message arrives, AI reads it, rules decide, then it is handled or a person approves it",
    )
    top, center, bottom = 170, 245, 320
    message, read, rules, act, done = 40, 265, 490, 715, 950
    c.wire(right(message, center), left(read, center))
    c.wire(right(read, center), left(rules, center))
    c.wire(right(rules, center), left(act, top))
    c.wire(right(rules, center), left(act, bottom), rose=True)
    c.wire(right(act, top), left(done, center))
    c.wire(right(act, bottom), left(done, center), rose=True)
    c.node(message, center, "Message arrives", "contact form")
    c.node(read, center, "AI reads it", "type and details")
    c.node(rules, center, "Rules decide", "safe to act alone?", rose=True)
    c.node(act, top, "Handled alone", "low risk")
    c.node(act, bottom, "Person approves", "unsure or risky", rose=True)
    c.node(done, center, "Systems updated", "HubSpot and Slack")
    c.ports(
        right(message, center),
        right(read, center),
        right(rules, center),
        right(act, top),
        right(act, bottom),
    )
    c.save("flow")


def architecture() -> None:
    c = Canvas(
        590,
        "Architecture",
        "A queue separates fast replies from slow work.",
        "fig. 02 — the system",
        "A contact form calls the API, which saves to a database. A worker takes items and calls "
        "Gemini, RDAP, HubSpot and Slack. Slack button clicks return to the API.",
    )
    y = 255
    form, api, db, worker, services = 40, 265, 490, 715, 950
    service_h = 72
    rows = [
        (155, "Gemini", "reads the message"),
        (240, "RDAP", "checks the domain"),
        (325, "HubSpot", "contacts, OAuth"),
        (410, "Slack", "summaries, buttons"),
    ]
    c.wire(right(form, y), left(api, y))
    c.wire(right(api, y), left(db, y))
    c.wire(right(db, y), left(worker, y))
    for row, _, _ in rows:
        c.wire(right(worker, y), left(services, row, service_h))
    c.path(f"M 1040 482 C 1040 545, 355 545, 355 {y + NODE_H + 4}", rose=True)
    c.node(form, y, "Contact form", "signed webhook")
    c.node(api, y, "API", "verifies, replies fast")
    c.node(db, y, "Database", "queue and audit log")
    c.node(worker, y, "Worker", "retries safely", rose=True)
    for row, name, detail in rows:
        c.node(services, row, name, detail, h=service_h)
    c.ports(right(form, y), right(api, y), right(db, y), right(worker, y))
    c.pill(697, 513, "signed approval click")
    c.save("architecture")


def reliability() -> None:
    c = Canvas(
        520,
        "Reliability",
        "One record, even when things fail.",
        "fig. 03 — five layers against duplicates",
        "Five failures and how the system responds to each",
    )
    rows = [
        ("The same webhook arrives twice", "A unique key ignores the copy"),
        ("The worker crashes midway", "It resumes at the unfinished step"),
        ("HubSpot's reply gets lost", "Upsert updates the same contact"),
        ("Slack's reply gets lost", "It finds the earlier post first"),
        ("An approver double-clicks", "Only the first click counts"),
    ]
    c.text(40, 165, "IF THIS HAPPENS", 12, MUTED, MONO, letter_spacing="1.5")
    c.text(620, 165, "THE SYSTEM", 12, MUTED, MONO, letter_spacing="1.5")
    for index, (problem, answer) in enumerate(rows):
        y = 180 + index * 58
        c.parts.append(f'<line x1="40" x2="{WIDTH - 40}" y1="{y}" y2="{y}" stroke="{HAIRLINE}"/>')
        c.text(40, y + 36, problem, 19, MUTED)
        c.path(f"M 500 {y + 30} L 590 {y + 30}", rose=True)
        c.text(620, y + 36, answer, 19, INK, SANS, font_weight="600")
    c.parts.append(f'<line x1="40" x2="{WIDTH - 40}" y1="470" y2="470" stroke="{HAIRLINE}"/>')
    c.save("reliability")


def approval() -> None:
    c = Canvas(
        420,
        "Human approval",
        "Flagged items write nothing until a person says yes.",
        "fig. 04 — the approval step",
        "Rules flag an item, Slack asks a person, the person clicks approve, HubSpot is updated",
    )
    y = 185
    xs = (40, 335, 630, 925)
    for start, end in pairwise(xs):
        c.wire(right(start, y, w=205), left(end, y), rose=start == xs[1])
    c.node(xs[0], y, "Rules flag it", "unsure or risky", w=205)
    c.node(xs[1], y, "Slack asks", "approve or reject", w=205)
    c.node(xs[2], y, "A person decides", "only listed approvers", rose=True, w=205)
    c.node(xs[3], y, "HubSpot updated", "once, and logged", w=205)
    c.ports(*(right(x, y, w=205) for x in xs[:3]))
    c.pill(732, 325, "reject: nothing is written")
    c.save("approval")


def lifecycle() -> None:
    c = Canvas(
        560,
        "Status",
        "Every message is always in one known state.",
        "fig. 05 — the life of a message",
        "A message is queued, then processed, then done, discarded, failed or waiting on a person",
    )
    queued, processing, outcome, final = 40, 300, 590, 900
    y, h = 280, 72
    rows = [
        (160, "Done", "systems updated"),
        (245, "Discarded", "confident spam"),
        (330, "Failed", "set aside, not lost"),
    ]
    waiting_y = 415
    c.wire(right(queued, y, h), left(processing, y, h))
    for row, _, _ in rows:
        c.wire(right(processing, y, h), left(outcome, row, h))
    c.wire(right(processing, y, h), left(outcome, waiting_y, h), rose=True)
    c.wire(right(outcome, waiting_y, h, 200), left(final, waiting_y, h), rose=True)
    c.path(f"M 390 {y} C 390 205, 130 205, 130 {y - 4}")
    c.path(f"M 680 {waiting_y + h} C 680 535, 130 535, 130 {y + h + 4}", rose=True)
    c.node(queued, y, "Queued", "ready to process", h=h)
    c.node(processing, y, "Processing", "worker has a lease", h=h)
    for row, title, detail in rows:
        c.node(outcome, row, title, detail, h=h)
    c.node(outcome, waiting_y, "Waiting on a person", "in Slack", rose=True, h=h, w=200)
    c.node(final, waiting_y, "Rejected", "nothing written", h=h)
    c.pill(260, 223, "retry with backoff")
    c.pill(405, 507, "approved")
    c.save("lifecycle")


if __name__ == "__main__":
    flow()
    architecture()
    reliability()
    approval()
    lifecycle()
