"""Draws docs/assets/system-map.svg: the detailed workflow-canvas view of the whole system."""

from html import escape
from pathlib import Path

W, H = 1740, 690
NODE_W, NODE_H = 140, 92
BG, DOT, CARD, BORDER, LINE = "#161616", "#3d3d3d", "#212121", "#616161", "#8f8f8f"
INK, MUTED, PINK, PINK_SOFT, DARK_INK = "#fafafa", "#c4c4c4", "#ff91ac", "#ffbcca", "#212121"
MONO = "Menlo, Consolas, monospace"
SANS = "Helvetica, Arial, sans-serif"

parts: list[str] = []


def add_text(
    x: float, y: float, words: str, size: int, fill: str, font: str = SANS, **extra: str
) -> None:
    attrs = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in extra.items())
    parts.append(
        f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}"{attrs}>'
        f"{escape(words)}</text>"
    )


def group(x: int, y: int, w: int, h: int, label: str) -> None:
    parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="#1c1c1c" stroke="#474747"/>'
    )
    add_text(x + 18, y + h - 12, label.upper(), 12, MUTED, MONO, letter_spacing="1.2")


def node(
    x: int,
    y: int,
    kind: str,
    title: str,
    detail: str = "",
    accent: bool = False,
    h: int = NODE_H,
    w: int = NODE_W,
) -> None:
    fill, stroke = (PINK_SOFT, PINK) if accent else (CARD, BORDER)
    main, sub = (DARK_INK, DARK_INK) if accent else (INK, MUTED)
    parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>'
    )
    add_text(x + 14, y + 24, kind.upper(), 10, sub, MONO, letter_spacing="1")
    add_text(x + 14, y + 48, title, 15, main, SANS, font_weight="600")
    for index, line in enumerate(detail.split("|") if detail else []):
        add_text(x + 14, y + 67 + index * 16, line, 12, sub)


def wire(
    start: tuple[float, float],
    end: tuple[float, float],
    vertical: bool = False,
    pink: bool = False,
    both: bool = False,
) -> None:
    (x1, y1), (x2, y2) = start, end
    color = PINK if pink else LINE
    if vertical:
        bend = abs(y2 - y1) * 0.5 * (1 if y2 > y1 else -1)
        curve = f"C {x1} {y1 + bend}, {x2} {y2 - bend}, {x2} {y2}"
    else:
        bend = max(abs(x2 - x1) * 0.5, 30)
        curve = f"C {x1 + bend} {y1}, {x2 - bend} {y2}, {x2} {y2}"
    marker = "url(#pink)" if pink else "url(#grey)"
    start_marker = f' marker-start="{marker}"' if both else ""
    parts.append(
        f'<path d="M {x1} {y1} {curve}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" marker-end="{marker}"{start_marker}/>'
    )


def dots(*points: tuple[float, float]) -> None:
    for x, y in points:
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="4.5" fill="{BG}" stroke="{LINE}" stroke-width="2"/>'
        )


def pill(x: float, y: float, words: str) -> None:
    width = len(words) * 7.1 + 22
    parts.append(
        f'<rect x="{x - width / 2}" y="{y - 13}" width="{width}" height="26" rx="13" '
        f'fill="#303030" stroke="#474747"/>'
    )
    add_text(x, y + 4, words, 12, INK, SANS, text_anchor="middle")


def main() -> None:
    parts.extend(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
            f'height="{H}" role="img" aria-label="Multi agent triage system map">',
            "<defs>",
            '<pattern id="canvas" width="22" height="22" patternUnits="userSpaceOnUse">'
            f'<circle cx="2" cy="2" r="1.2" fill="{DOT}"/></pattern>',
            *(
                f'<marker id="{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" '
                f'fill="{color}"/></marker>'
                for name, color in (("grey", LINE), ("pink", PINK))
            ),
            "</defs>",
            f'<rect width="{W}" height="{H}" fill="{BG}"/>',
            f'<rect width="{W}" height="{H}" fill="url(#canvas)"/>',
        ]
    )
    add_text(40, 46, "MULTI AGENT TRIAGE", 13, MUTED, MONO, letter_spacing="1.5")
    add_text(
        40, 82, "Automates the routine. Asks a person about the rest.", 26, INK, SANS,
        font_weight="500",
    )  # fmt: skip

    main_y = 330
    mid = main_y + NODE_H / 2
    group(290, 270, 360, 190, "API process: answers fast")
    group(990, 270, 720, 190, "Worker process: slow, retryable work")

    # Wires go first so nodes and labels sit on top of them.
    wire((180, mid), (304, mid))
    wire((450, mid), (484, mid))
    wire((630, mid), (734, mid))
    wire((910, mid), (1004, mid))
    wire((1150, mid), (1184, mid))
    wire((1330, mid), (1364, mid))
    wire((1510, mid), (1544, mid))
    wire((1080, 194), (1080, main_y), vertical=True, both=True)
    wire((1260, 194), (1260, main_y), vertical=True, both=True)
    wire((1300, main_y), (1410, 194), vertical=True, both=True)
    wire((1620, main_y), (1520, 194), vertical=True)
    wire((1440, main_y + NODE_H), (1520, 556), vertical=True, pink=True)
    wire((1620, main_y + NODE_H), (1590, 556), vertical=True)
    wire((1480, 606), (1244, 606), pink=True)
    parts.append(
        f'<path d="M 1100 606 C 960 606, 825 560, 825 438" fill="none" stroke="{PINK}" '
        'stroke-width="2" stroke-linecap="round" marker-end="url(#pink)"/>'
    )

    node(40, main_y, "Trigger", "Contact form", "or email forwarder")
    node(310, main_y, "Security", "Verify input", "signature, schema")
    node(490, main_y, "Reliability", "Dedupe", "idempotency key")
    node(
        740,
        main_y - 10,
        "Database",
        "SQLite",
        "queue · step ledger|audit log · tokens",
        h=112,
        w=170,
    )
    node(1010, main_y, "AI", "Classify, extract", "validated JSON")
    node(1190, main_y, "Enrich", "Add context", "domain age, CRM")
    node(1370, main_y, "Rules in code", "Route", "act or ask?", accent=True)
    node(1550, main_y, "Action", "Act", "update and notify")
    node(1010, 100, "AI model", "Gemini API", "free tier")
    node(1190, 100, "Outside API", "RDAP", "domain age")
    node(1370, 100, "CRM · OAuth 2.0", "HubSpot", "contacts", w=190)
    node(1480, 560, "Chat", "Slack", "summary, buttons")
    node(1100, 560, "Human in the loop", "Approver", "approve or reject", accent=True)

    dots((180, mid), (310, mid), (450, mid), (490, mid), (630, mid), (740, mid))
    dots((910, mid), (1010, mid), (1150, mid), (1190, mid), (1330, mid), (1370, mid))
    dots((1510, mid), (1550, mid))

    pill(245, mid, "signed webhook")
    pill(695, mid, "enqueue")
    pill(960, mid, "claim")
    pill(1530, 308, "confident, low risk")
    pill(1480, 491, "unsure or risky")
    pill(1605, 491, "summary")
    pill(1360, 606, "approval request")
    pill(910, 568, "signed button click")
    pill(1610, 240, "upsert by email")

    parts.append("</svg>")
    Path("docs/assets/system-map.svg").write_text("\n".join(parts) + "\n")
    print(f"system-map {W},{H}")


if __name__ == "__main__":
    main()
