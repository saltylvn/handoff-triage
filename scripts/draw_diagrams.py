"""Draws the README visuals as plain SVG: one idea per image, in plain words.

The look matches the system map: an off-black canvas with a dot grid, gray cards with mono labels,
connector dots, curved wires with solid arrowheads, and one soft pink accent. Positions are explicit
because automatic layout made these too busy to read."""

from html import escape
from itertools import pairwise
from pathlib import Path

# Shared with scripts/draw_system_map.py.
BG, DOT, CARD, HAIRLINE = "#161616", "#3d3d3d", "#212121", "#616161"
INK, MUTED, LINE = "#fafafa", "#c4c4c4", "#8f8f8f"
ROSE, ROSE_FILL, ON_ROSE = "#ff91ac", "#ffbcca", "#212121"
PILL, PILL_EDGE = "#303030", "#474747"
SANS = "Helvetica, Arial, sans-serif"
MONO = "Menlo, Consolas, monospace"
WIDTH = 1170
NODE_W, NODE_H = 180, 92

Point = tuple[float, float]


class Canvas:
    def __init__(self, height: int, eyebrow: str, headline: str, label: str) -> None:
        self.height = height
        self.ports: list[Point] = []
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(label)}">',
            '<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
            f'<circle cx="2" cy="2" r="1.2" fill="{DOT}"/></pattern>',
            *(
                f'<marker id="{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" '
                f'fill="{color}"/></marker>'
                for name, color in (("grey", LINE), ("rose", ROSE))
            ),
            "</defs>",
            f'<rect width="{WIDTH}" height="{height}" fill="{BG}"/>',
            f'<rect width="{WIDTH}" height="{height}" fill="url(#dots)"/>',
        ]
        self.text(40, 50, eyebrow.upper(), 13, MUTED, MONO, letter_spacing="1.5")
        self.text(40, 92, headline, 32, INK, SANS, font_weight="500")

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
        kind: str = "",
    ) -> None:
        main, sub = (ON_ROSE, ON_ROSE) if rose else (INK, MUTED)
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
            f'fill="{ROSE_FILL if rose else CARD}" stroke="{ROSE if rose else HAIRLINE}" '
            'stroke-width="1.5"/>'
        )
        if kind:
            self.text(x + 16, y + 24, kind.upper(), 10, sub, MONO, letter_spacing="1")
            title_y = y + 50
        else:
            title_y = y + h / 2 - 3
        self.text(x + 16, title_y, title, 17, main, SANS, font_weight="600")
        if detail:
            self.text(x + 16, title_y + 21, detail, 13, sub)

    def wire(self, start: Point, end: Point, rose: bool = False) -> None:
        """A horizontal S-curve between connector dots, like a workflow editor."""
        (x1, y1), (x2, y2) = start, end
        tip = x2 - 6  # the arrowhead stops just short of the dot
        bend = max(abs(tip - x1) * 0.5, 24)
        self.path(f"M {x1} {y1} C {x1 + bend} {y1}, {tip - bend} {y2}, {tip} {y2}", rose)
        self.ports.extend([start, end])

    def path(self, d: str, rose: bool = False) -> None:
        marker = "url(#rose)" if rose else "url(#grey)"
        self.parts.insert(
            self._wires_at(),
            f'<path d="{d}" fill="none" stroke="{ROSE if rose else LINE}" stroke-width="2" '
            f'stroke-linecap="round" marker-end="{marker}"/>',
        )

    def _wires_at(self) -> int:
        """Wires go straight after the background and headline, so cards sit on top of them."""
        return 8

    def pill(self, x: float, y: float, words: str) -> None:
        width = len(words) * 7.1 + 24
        self.parts.append(
            f'<rect x="{x - width / 2}" y="{y - 13}" width="{width}" height="26" rx="13" '
            f'fill="{PILL}" stroke="{PILL_EDGE}"/>'
        )
        self.text(x, y + 4.5, words, 13, INK, SANS, text_anchor="middle")

    def save(self, name: str) -> None:
        pills = [part for part in self.parts if 'rx="13"' in part or 'text-anchor="middle"' in part]
        self.parts = [part for part in self.parts if part not in pills]
        for x, y in dict.fromkeys(self.ports):
            self.parts.append(
                f'<circle cx="{x}" cy="{y}" r="4.5" fill="{BG}" stroke="{LINE}" stroke-width="2"/>'
            )
        self.parts.extend(pills)
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
    c.node(message, center, "Message arrives", "contact form", kind="Trigger")
    c.node(read, center, "AI reads it", "type and details", kind="AI")
    c.node(rules, center, "Rules decide", "safe to act alone?", rose=True, kind="Rules in code")
    c.node(act, top, "Handled alone", "low risk", kind="Automatic")
    c.node(act, bottom, "Person approves", "unsure or risky", rose=True, kind="Human in the loop")
    c.node(done, center, "Systems updated", "HubSpot and Slack", kind="Action")
    c.save("flow")


def architecture() -> None:
    c = Canvas(
        620,
        "Architecture",
        "A queue separates fast replies from slow work.",
        "A contact form calls the API, which saves to a database. A worker takes items and calls "
        "Gemini, RDAP, HubSpot and Slack. Slack button clicks return to the API.",
    )
    y = 255
    form, api, db, worker, services = 40, 265, 490, 715, 950
    service_h = 92
    rows = [
        (125, "Gemini", "reads the message", "AI model"),
        (225, "RDAP", "checks the domain", "Outside API"),
        (325, "HubSpot", "contacts", "CRM · OAuth 2.0"),
        (425, "Slack", "summaries, buttons", "Chat"),
    ]
    c.wire(right(form, y), left(api, y))
    c.wire(right(api, y), left(db, y))
    c.wire(right(db, y), left(worker, y))
    for row, _, _, _ in rows:
        c.wire(right(worker, y), left(services, row, service_h))
    c.path(f"M 1040 517 C 1040 585, 355 585, 355 {y + NODE_H + 4}", rose=True)
    c.node(form, y, "Contact form", "signed webhook", kind="Trigger")
    c.node(api, y, "API", "verifies, replies fast", kind="Security")
    c.node(db, y, "Database", "queue and audit log", kind="Reliability")
    c.node(worker, y, "Worker", "retries safely", rose=True, kind="Slow work")
    for row, name, detail, kind in rows:
        c.node(services, row, name, detail, h=service_h, kind=kind)
    c.pill(697, 551, "signed approval click")
    c.save("architecture")


def reliability() -> None:
    c = Canvas(
        520,
        "Reliability",
        "One record, even when things fail.",
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
        "Rules flag an item, Slack asks a person, the person clicks approve, HubSpot is updated",
    )
    y = 185
    xs = (40, 335, 630, 925)
    for start, end in pairwise(xs):
        c.wire(right(start, y, w=205), left(end, y), rose=start == xs[1])
    c.node(xs[0], y, "Rules flag it", "unsure or risky", w=205, kind="Rules in code")
    c.node(xs[1], y, "Slack asks", "approve or reject", w=205, kind="Chat")
    c.node(
        xs[2],
        y,
        "A person decides",
        "only listed approvers",
        rose=True,
        w=205,
        kind="Human in the loop",
    )
    c.node(xs[3], y, "HubSpot updated", "once, and logged", w=205, kind="CRM · OAuth 2.0")
    c.pill(732, 325, "reject: nothing is written")
    c.save("approval")


def lifecycle() -> None:
    c = Canvas(
        560,
        "Status",
        "Every message is always in one known state.",
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


def social_preview() -> None:
    """The image GitHub shows when the repo link is shared: 1280 by 640."""
    w, h = 1280, 640
    stats = (
        ("84%", "handled alone"),
        ("97%", "correct when acting alone"),
        ("0 of 4", "sensitive messages acted on alone"),
    )

    def text(x: float, y: float, words: str, size: int, fill: str, extra: str = "") -> str:
        return (
            f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" fill="{fill}" {extra}>'
            f"{escape(words)}</text>"
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1.2" fill="{DOT}"/></pattern></defs>',
        f'<rect width="{w}" height="{h}" fill="{BG}"/>',
        f'<rect width="{w}" height="{h}" fill="url(#dots)"/>',
        text(
            80,
            111,
            "HUMAN-IN-THE-LOOP TRIAGE",
            20,
            MUTED,
            f'font-family="{MONO}" letter-spacing="3"',
        ).replace(f'font-family="{SANS}" ', "", 1),
        text(80, 215, "Automates the routine.", 72, INK, 'font-weight="500" letter-spacing="-1"'),
        text(
            80,
            300,
            "Asks a person about the rest.",
            72,
            ROSE,
            'font-weight="500" letter-spacing="-1"',
        ),
    ]
    for index, (value, label) in enumerate(stats):
        x = 80 + index * 380
        parts.append(text(x, 425, value, 56, INK, 'font-weight="600" letter-spacing="-1"'))
        parts.append(text(x, 462, label, 20, MUTED))
    parts.append(text(80, 560, "70 held-out synthetic messages", 18, MUTED))
    parts.append("</svg>")
    Path("docs/assets/social-preview.svg").write_text("\n".join(parts) + "\n")
    print(f"social-preview {w},{h}")


if __name__ == "__main__":
    social_preview()
    flow()
    architecture()
    reliability()
    approval()
    lifecycle()
