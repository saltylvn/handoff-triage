"""Hub-and-spoke canvas pages for docs/assets: the agent in the middle, working panels around it,
dashed connectors labeled with what flows. Each page shows one layer of the same system:
reliability, decisions, integrations. Run through scripts/render-diagrams.sh."""

import base64
import sys
from html import escape
from pathlib import Path

OUT = Path(sys.argv[1])
W, H, M = 1600, 1200, 64

BG, DOT = "#f3f2f1", "#dedad6"
PANEL, PANEL_EDGE = "#f8f8f7", "#e7e5e4"
WHITE, WHITE_EDGE, ROW_RULE = "#ffffff", "#ebe9e7", "#f0eeec"
INK, MUTED, SOFT = "#292524", "#6f6964", "#9a938d"
ACCENT, TINT, ACCENT_INK = "#7d8ff2", "#eef0fd", "#4553b8"
DARK, DASH = "#161618", "#c4bfba"
GREEN, GREEN_DOT, AMBER, RED_DOT = "#0b7a3b", "#00c950", "#f0a020", "#fb2c36"

SANS = "'Helvetica Now Display', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono Local', 'Geist Mono', Menlo, monospace"
URL = "github.com/saltylvn/human-in-the-loop-triage"
SF_MONO = Path(
    "/System/Applications/Utilities/Terminal.app/Contents/Resources/Fonts/SF-Mono-Regular.otf"
)
ICON_DIR = Path(__file__).parent / "icons"
ICON_NAMES = ("Gemini", "RDAP", "HubSpot", "Slack")
_GEMINI = (ICON_DIR / "gemini.svg").read_text().split(' d="')[1].split('"')[0]


def _png(name):
    return "data:image/png;base64," + base64.b64encode((ICON_DIR / name).read_bytes()).decode()


_PNG = {"Slack": _png("slack.png"), "HubSpot": _png("hubspot.png")}

TILES = (
    ("G", "Gemini", "#3b78e7"),
    ("R", "RDAP", "#9a938d"),
    ("H", "HubSpot", "#e8613c"),
    ("S", "Slack", "#611f69"),
)

# satellite frames: x, y, w (heights vary per page)
LEFT_X, RIGHT_X, SAT_W = 64, 1066, 470
HUB = (600, 420, 400, 340)


def text_width(words, size, mono=False):
    if mono:
        return len(words) * size * 0.61
    total = 0.0
    for ch in words:
        if ch in "il.,'·|: ()":
            total += 0.28
        elif ch in "mwMW":
            total += 0.83
        elif ch.isupper() or ch.isdigit():
            total += 0.64
        else:
            total += 0.53
    return total * size


class Canvas:
    def __init__(self, name, number, topic, headline, pill, layer, label):
        self.name, self.label = name, label
        self.back, self.front = [], []
        tag = topic
        self.rect(M, 40, text_width(tag, 15, True) + 32, 34, "none", PANEL_EDGE, r=17)
        self.text(M + 16, 62, tag, 15, MUTED, MONO)
        self.text(W - M, 64, "Human-in-the-Loop Triage", 20, MUTED, anchor="end", weight=500)
        for i, (words, color) in enumerate(headline):
            self.text(M, 132 + i * 58, words, 52, color, weight=500, spacing=-1.5)
        self.hub(pill)
        self.text(W / 2, 1118, layer.upper(), 16, MUTED, MONO, anchor="middle", spacing=5)
        self.text(M, H - 36, f"Tyler Clark  ·  {URL}", 18, MUTED)

    # primitives
    def text(self, x, y, words, size, fill=INK, font=SANS, weight=None, anchor=None, spacing=None):
        attrs = f' font-weight="{weight}"' if weight else ""
        attrs += f' text-anchor="{anchor}"' if anchor else ""
        attrs += f' letter-spacing="{spacing}"' if spacing is not None else ""
        self.front.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" fill="{fill}"{attrs} xml:space="preserve">'
            f"{escape(words)}</text>"
        )

    def rect(self, x, y, w, h, fill, edge=None, r=16, shadow=False):
        stroke = f' stroke="{edge}" stroke-width="1.2"' if edge else ""
        filt = ' filter="url(#soft)"' if shadow else ""
        self.front.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}"{stroke}{filt}/>'
        )

    def icon(self, name, x, y, size=20):
        """The real Slack and HubSpot app icons, the Gemini sparkle, and a plain globe for RDAP."""
        if name == "Gemini":
            self.front.append(
                f'<path d="{_GEMINI}" fill="url(#gemini)" transform="translate({x:.1f} {y:.1f}) scale({size / 24:.4f})"/>'
            )
        elif name == "Form":
            self.front.append(
                f'<g fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-linecap="round">'
                f'<rect x="{x + 2:.1f}" y="{y + 1:.1f}" width="{size - 4:.1f}" height="{size - 2:.1f}" rx="3"/>'
                f'<line x1="{x + 6:.1f}" y1="{y + size * 0.35:.1f}" x2="{x + size - 6:.1f}" y2="{y + size * 0.35:.1f}"/>'
                f'<line x1="{x + 6:.1f}" y1="{y + size * 0.6:.1f}" x2="{x + size * 0.6:.1f}" y2="{y + size * 0.6:.1f}"/></g>'
            )
        elif name == "RDAP":
            r, cx, cy = size / 2 - 1, x + size / 2, y + size / 2
            self.front.append(
                f'<g fill="none" stroke="{MUTED}" stroke-width="1.4"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}"/>'
                f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{r * 0.45:.1f}" ry="{r:.1f}"/>'
                f'<line x1="{cx - r:.1f}" y1="{cy:.1f}" x2="{cx + r:.1f}" y2="{cy:.1f}"/></g>'
            )
        else:
            self._clip = getattr(self, "_clip", 0) + 1
            cid = f"icon{self._clip}"
            radius = size * 0.24 if name == "HubSpot" else 0
            self.front.append(
                f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" rx="{radius:.1f}"/></clipPath>'
                f'<image href="{_PNG[name]}" x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" clip-path="url(#{cid})"/>'
            )

    def dot(self, x, y, color, r=4.5):
        self.front.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}"/>')

    def check(self, x, y, ok=True):
        """A round toggle like the reference: green check, or a red block sign."""
        self.front.append(
            f'<circle cx="{x}" cy="{y}" r="15" fill="{WHITE}" stroke="{WHITE_EDGE}" stroke-width="1.2"/>'
        )
        if ok:
            self.front.append(
                f'<path d="M {x - 6} {y} L {x - 2} {y + 4} L {x + 6} {y - 5}" fill="none" stroke="{GREEN}" '
                'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            )
        else:
            self.front.append(
                f'<circle cx="{x}" cy="{y}" r="7" fill="none" stroke="#c10007" stroke-width="2"/>'
            )
            self.front.append(
                f'<line x1="{x - 5}" y1="{y + 5}" x2="{x + 5}" y2="{y - 5}" stroke="#c10007" stroke-width="2"/>'
            )

    def status(self, x_right, y, words, color, size=15):
        """A white pill with a colored dot, right-aligned at x_right, centered on y."""
        w = text_width(words, size, True) + 44
        x = x_right - w
        self.rect(x, y - 16, w, 32, WHITE, WHITE_EDGE, r=16)
        self.dot(x + 16, y, color)
        self.text(x + 28, y + 5, words, size, INK, MONO)
        return w

    def chip(
        self,
        x,
        y,
        words,
        size=14,
        fill=WHITE,
        edge=WHITE_EDGE,
        color=INK,
        h=28,
        right=False,
        icon=None,
    ):
        pad = size + 8 if icon else 0
        w = text_width(words, size, True) + 22 + pad
        if right:
            x -= w
        self.rect(x, y, w, h, fill, edge, r=h / 2)
        if icon:
            self.icon(icon, x + 11, y + (h - size - 2) / 2, size + 2)
        self.text(
            x + pad + (w - pad) / 2,
            y + h / 2 + size * 0.36,
            words,
            size,
            color,
            MONO,
            anchor="middle",
        )
        return w

    def pill_label(self, cx, cy, words):
        w = text_width(words, 14, True) + 28
        self.rect(cx - w / 2, cy - 14, w, 28, BG, PANEL_EDGE, r=14)
        self.text(cx, cy + 5, words, 14, SOFT, MONO, anchor="middle")

    def connector(self, points, label, at):
        d = "M " + " L ".join(f"{x} {y}" for x, y in points)
        self.back.append(
            f'<path d="{d}" fill="none" stroke="{DASH}" stroke-width="1.5" stroke-dasharray="5 5"/>'
        )
        for x, y in (points[0], points[-1]):
            self.back.append(
                f'<circle cx="{x}" cy="{y}" r="6" fill="{BG}" stroke="{DASH}" stroke-width="1.5"/>'
            )
        self.pill_label(*at, label)

    def panel(self, x, y, w, h, title, count=None, status=None, status_color=None, icon=None):
        """Outer faint panel with a grey header, and a white inner card. Returns the inner card."""
        self.rect(x, y, w, h, PANEL, PANEL_EDGE, r=30)
        tx = x + 28
        if icon:
            self.icon(icon, tx, y + 22, 20)
            tx += 30
        self.text(tx, y + 38, title, 18, SOFT, weight=500)
        if count is not None:
            cx = tx + text_width(title, 18) + 12
            self.rect(cx, y + 22, 24, 22, WHITE, WHITE_EDGE, r=6)
            self.text(cx + 12, y + 38, str(count), 13, MUTED, MONO, anchor="middle")
        if status:
            sx = x + w - 28 - text_width(status, 16) * 0.97
            self.text(sx, y + 38, status, 16, MUTED)
            if status_color:
                self.dot(sx - 12, y + 33, status_color)
        ix, iy, iw, ih = x + 12, y + 58, w - 24, h - 70
        self.rect(ix, iy, iw, ih, WHITE, WHITE_EDGE, r=22, shadow=True)
        return ix, iy, iw, ih

    def rule(self, x1, x2, y):
        self.front.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{ROW_RULE}" stroke-width="1.2"/>'
        )

    def hub(self, pill):
        x, y, w, h = HUB
        pw = text_width(pill, 16, True) + 40
        self.rect(W / 2 - pw / 2, y - 64, pw, 38, BG, PANEL_EDGE, r=19)
        self.text(W / 2, y - 39, pill, 16, INK, MONO, anchor="middle")
        self.rect(x, y, w, h, PANEL, PANEL_EDGE, r=36)
        ix, iy = x + 12, y + 12
        self.rect(ix, iy, w - 24, h - 24, WHITE, WHITE_EDGE, r=28, shadow=True)
        self.dot(ix + 40, iy + 50, ACCENT, r=5)
        self.text(ix + 54, iy + 56, "New message on the contact form", 17, SOFT)
        self.text(ix + 38, iy + 118, "Inbound Triage", 38, INK, weight=500, spacing=-1)
        self.text(ix + 38, iy + 162, "Agent", 38, INK, weight=500, spacing=-1)
        for i, (_, name, _color) in enumerate(TILES):
            row, col = divmod(i, 2)
            cx, cy = ix + 38 + col * 158, iy + 196 + row * 48
            self.rect(cx, cy, 146, 38, PANEL, WHITE_EDGE, r=12)
            self.icon(name, cx + 12, cy + 9, 20)
            self.text(cx + 42, cy + 25, name, 17, INK, weight=500)

    def wire_left_top(self, bottom, y, label):
        """From the top-left panel's bottom edge down to the hub's left side."""
        assert bottom < y - 16, (bottom, y)
        self.connector([(300, bottom), (300, y), (HUB[0], y)], label, (450, y))

    def wire_right_top(self, bottom, y, label):
        assert bottom < y - 16, (bottom, y)
        self.connector([(HUB[0] + HUB[2], y), (1300, y), (1300, bottom)], label, (1150, y))

    def wire_left_bottom(self, top, y, label):
        assert top < y - 30, (top, y)
        self.connector([(760, HUB[1] + HUB[3]), (760, y), (LEFT_X + SAT_W, y)], label, (647, y))

    def wire_right_bottom(self, top, y, label):
        assert top < y - 30, (top, y)
        self.connector([(840, HUB[1] + HUB[3]), (840, y), (RIGHT_X, y)], label, (953, y))

    def save(self, size=(W, H)):
        width, height = size
        font = ""
        if SF_MONO.exists():
            data = base64.b64encode(SF_MONO.read_bytes()).decode()
            font = (
                f"@font-face{{font-family:'SF Mono Local';src:url(data:font/otf;base64,{data});}}"
            )
        doc = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{escape(self.label)}">',
            f"<defs><style>{font}</style>",
            '<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
            f'<circle cx="2" cy="2" r="1.1" fill="{DOT}"/></pattern>',
            '<filter id="soft" x="-10%" y="-10%" width="120%" height="140%">'
            '<feDropShadow dx="0" dy="3" stdDeviation="7" flood-color="#292524" flood-opacity="0.06"/></filter>',
            '<linearGradient id="gemini" x1="0" y1="1" x2="1" y2="0">'
            '<stop offset="0" stop-color="#3186ff"/><stop offset="0.55" stop-color="#8c6ff7"/>'
            '<stop offset="1" stop-color="#d96570"/></linearGradient>',
            "</defs>",
            f'<rect width="{width}" height="{height}" fill="{BG}"/>',
            f'<rect width="{width}" height="{height}" fill="url(#dots)"/>',
        ]
        doc += self.back + self.front + ["</svg>"]
        (OUT / f"{self.name}.svg").write_text("\n".join(doc) + "\n")
        print(self.name, f"{width},{height}")


def log_rows(c, ix, iy, iw, rows, row_h=70, top=18):
    """Timestamped rows: time, name, detail underneath, status pill on the right."""
    for i, (time, name, detail, status, color) in enumerate(rows):
        y = iy + top + i * row_h
        if i:
            c.rule(ix + 20, ix + iw - 20, y - 8)
        c.text(ix + 22, y + 24, time, 14, SOFT, MONO)
        if name in ICON_NAMES:
            c.icon(name, ix + 112, y + 9, 18)
            c.text(ix + 140, y + 24, name, 16, INK, MONO)
        else:
            c.text(ix + 112, y + 24, name, 16, INK, MONO)
        c.text(ix + (140 if name in ICON_NAMES else 112), y + 48, detail, 14, SOFT, MONO)
        c.status(ix + iw - 18, y + 20, status, color, 14)


def reliability():
    c = Canvas(
        "system-design",
        1,
        "System design",
        [("Nothing lost, nothing done twice.", INK), ("Failures resume where they stopped.", SOFT)],
        "accepted messages are never lost.",
        "Reliability layer",
        "System design, the reliability layer. In the middle, the Inbound Triage Agent, connected to Gemini, RDAP, "
        "HubSpot and Slack. Around it: five intake checks before the API answers; one SQLite file with four tables; "
        "five detours such as approval, retry and failure; and a step ledger that lets a retry skip finished work.",
    )
    ix, iy, iw, _ = c.panel(LEFT_X, 236, SAT_W, 332, "Intake checks", count=5)
    checks = [
        ("Body under 64 KB", "else 413"),
        ("Valid HMAC signature, 5 min", "else 401"),
        ("Every field passes Pydantic", "else 400"),
        ("A repeat is accepted, not rerun", "202"),
        ("Stored, then answered", "202"),
    ]
    for i, (words, code) in enumerate(checks):
        y = iy + i * 52
        if i:
            c.rule(ix, ix + iw, y)
        c.text(ix + 22, y + 33, words, 18, INK)
        c.text(ix + iw - 62, y + 32, code, 14, SOFT, MONO, anchor="end")
        c.check(ix + iw - 32, y + 27)
    c.wire_left_top(568, 600, "checking request")

    ix, iy, iw, _ = c.panel(
        RIGHT_X, 236, SAT_W, 280, "Storage", count=4, status="one SQLite file, WAL"
    )
    tables = [
        ("items", "the queue"),
        ("steps", "step ledger"),
        ("decisions", "append-only log"),
        ("oauth_tokens", "encrypted"),
    ]
    for i, (name, words) in enumerate(tables):
        y = iy + i * 52
        if i:
            c.rule(ix, ix + iw, y)
        c.text(ix + 22, y + 33, name, 16, INK, MONO)
        c.text(ix + iw - 22, y + 33, words, 17, MUTED, anchor="end")
    c.wire_right_top(516, 560, "saving state")

    ix, iy, iw, _ = c.panel(LEFT_X, 648, SAT_W, 432, "Detours", count=5)
    detours = [
        ("Needs a person", "Waits for approval in Slack", "awaiting approval"),
        ("Temporary error", "Retried, 30 s doubling to 30 min", "queued"),
        ("Worker crashes", "Reclaimed after its 180 s lease", "processing"),
        ("Keeps failing", "Set aside, with a Slack alert", "failed"),
        ("Confident spam", "Discarded, and still logged", "discarded"),
    ]
    for i, (when, then, state) in enumerate(detours):
        y = iy + i * 72
        if i:
            c.rule(ix, ix + iw, y)
        c.text(ix + 22, y + 32, when, 18, INK, weight=500)
        c.text(ix + 22, y + 56, then, 15, SOFT)
        c.chip(ix + iw - 18, y + 14, state, 13, right=True)
    c.wire_left_bottom(648, 900, "« retrying")

    ix, iy, iw, _ih = c.panel(RIGHT_X, 640, SAT_W, 436, "Step ledger", status="example run")
    log_rows(
        c,
        ix,
        iy,
        iw,
        [
            ("09:14:02", "classify", "Gemini, schema-checked", "done", GREEN_DOT),
            ("09:14:03", "enrich", "domain age, CRM lookup", "done", GREEN_DOT),
            ("09:14:03", "route", "rules in code", "done", GREEN_DOT),
            ("09:14:04", "crm_upsert", "HubSpot, by email", "done", GREEN_DOT),
            ("09:14:05", "post_summary", "found the earlier post", "recovered", AMBER),
        ],
    )
    c.wire_right_bottom(640, 860, "logging »")
    c.save()


def decisions():
    c = Canvas(
        "ai-design",
        2,
        "AI design and evaluation",
        [("AI reads the message.", INK), ("Rules and evals decide the rest.", SOFT)],
        "the model reads. code decides.",
        "Decision layer",
        "AI design, the decision layer. Around the agent: the eight-field JSON contract Gemini must return; seven "
        "routing rules in code that send a message to a person; a pending Slack approval request with Reject and "
        "Approve; and evaluation results on 70 held-out synthetic messages.",
    )
    ix, iy, iw, _ = c.panel(
        LEFT_X, 236, SAT_W, 336, "Output contract", count=8, status="JSON schema"
    )
    fields = [
        ("category", "6 options"),
        ("urgency", "low · normal · high"),
        ("sensitive", "true · false"),
        ("confidence", "0 to 1"),
        ("company", "text or null"),
        ("team_size", "integer or null"),
        ("budget_usd", "number or null"),
        ("summary", "40 words at most"),
    ]
    for i, (name, kind) in enumerate(fields):
        y = iy + 6 + i * 32
        c.text(ix + 22, y + 22, name, 15, INK, MONO)
        c.text(ix + iw - 22, y + 22, kind, 14, SOFT, MONO, anchor="end")
    c.wire_left_top(572, 610, "reading the reply")

    ix, iy, iw, _ = c.panel(
        RIGHT_X,
        236,
        SAT_W,
        334,
        "Routing rules",
        count=7,
        status="send to a person",
        status_color=ACCENT,
    )
    rules = [
        "Confidence below 0.90",
        "Invalid AI reply",
        "Legal, security or deletion issue",
        "Team 500+ or budget $50,000+",
        "Urgent existing customer",
        "Existing customer marked spam",
        "Sales lead, domain under 30 days",
    ]
    for i, rule in enumerate(rules):
        y = iy + 8 + i * 34
        c.dot(ix + 26, y + 17, ACCENT)
        c.text(ix + 42, y + 23, rule, 17, INK)
    c.wire_right_top(570, 604, "applying rules")

    ix, iy, iw, _ = c.panel(
        LEFT_X,
        660,
        SAT_W,
        420,
        "Approval request",
        status="Pending",
        status_color=AMBER,
        icon="Slack",
    )
    c.text(ix + 24, iy + 42, "Sales lead, $250,000 budget", 21, INK, weight=500)
    c.text(ix + 24, iy + 70, "Held for a person at confidence 1.0", 16, SOFT)
    c.chip(ix + 24, iy + 88, "high_value", 13, fill=TINT, edge=ACCENT, color=ACCENT_INK)
    c.rect(ix + 24, iy + 136, 92, 40, PANEL, WHITE_EDGE, r=10)
    c.text(ix + 70, iy + 162, "Reject", 17, MUTED, anchor="middle", weight=500)
    c.rect(ix + 128, iy + 136, 124, 40, DARK, r=10)
    c.text(ix + 190, iy + 162, "✓ Approve", 17, WHITE, anchor="middle", weight=500)
    c.rule(ix, ix + iw, iy + 200)
    c.text(ix + 24, iy + 232, "IF NO RULE FIRES, IT RUNS ALONE", 13, SOFT, MONO, spacing=1)
    for i, (who, then) in enumerate(
        (
            ("Confident spam", "discarded"),
            ("Job seeker", "Slack only"),
            ("Everyone else", "HubSpot and Slack"),
        )
    ):
        y = iy + 266 + i * 30
        c.text(ix + 24, y, who, 17, INK)
        c.text(ix + iw - 24, y, then, 17, MUTED, anchor="end")
    c.wire_left_bottom(660, 900, "« asking a person")

    ix, iy, iw, _ih = c.panel(
        RIGHT_X, 640, SAT_W, 430, "Evaluation", status="70 held out, synthetic"
    )
    results = [
        ("handled alone", "59 of 70", "84.3%"),
        ("correct when alone", "57 of 59", "96.6%"),
        ("sensitive, to a person", "all flagged", "4 of 4"),
        ("prompt injections", "classified correctly", "3 of 3"),
        ("median model response", "95th percentile 7.5 s", "1.0 s"),
        ("model cost per 1,000", "at paid rates", "$0.33"),
    ]
    for i, (name, detail, value) in enumerate(results):
        y = iy + 8 + i * 58
        if i:
            c.rule(ix + 20, ix + iw - 20, y)
        c.text(ix + 22, y + 26, name, 17, INK)
        c.text(ix + 22, y + 47, detail, 13, SOFT, MONO)
        c.text(ix + iw - 22, y + 36, value, 24, INK, weight=500, anchor="end", spacing=-0.5)
    c.wire_right_bottom(640, 860, "measuring »")
    c.save()


def integrations():
    c = Canvas(
        "integrations-security",
        3,
        "Integrations, APIs and security",
        [("Every connection authenticated,", INK), ("retried safely and logged.", SOFT)],
        "every call authenticated and logged.",
        "Integration layer",
        "Integrations and security, the integration layer. Around the agent: HubSpot OAuth 2.0 in six steps; a retry "
        "budget showing attempt 2 of 6; four checks on every Slack approval click; and an example API log with Gemini, "
        "RDAP, HubSpot and Slack calls.",
    )
    ix, iy, iw, _ = c.panel(LEFT_X, 236, SAT_W, 338, "HubSpot OAuth 2.0", count=6, icon="HubSpot")
    steps = [
        ("Start", "random state, stored hashed"),
        ("Consent", "3 scopes, contacts only"),
        ("Callback", "state works once"),
        ("Exchange", "code for tokens, server side"),
        ("Encrypt", "AES-256-GCM at rest"),
        ("Refresh", "60 s early, again on 401"),
    ]
    for i, (title, words) in enumerate(steps):
        y = iy + i * 44
        if i:
            c.rule(ix, ix + iw, y)
        c.text(ix + 22, y + 29, str(i + 1), 14, SOFT, MONO)
        c.text(ix + 46, y + 29, title, 17, INK, weight=500)
        c.text(ix + iw - 22, y + 29, words, 15, MUTED, anchor="end")
    c.wire_left_top(574, 610, "authorizing")

    ix, iy, iw, _ = c.panel(RIGHT_X, 236, SAT_W, 300, "Retry budget", status="example")
    c.text(ix + 26, iy + 62, "Attempt 2", 40, INK, weight=500, spacing=-1)
    c.text(ix + 26 + text_width("Attempt 2", 40) - 6, iy + 62, " / 6", 22, SOFT)
    c.rect(ix + 26, iy + 88, iw - 52, 10, PANEL, r=5)
    c.rect(ix + 26, iy + 88, (iw - 52) / 3, 10, DARK, r=5)
    c.text(ix + 26, iy + 128, "Next try within 60 s", 16, MUTED)
    c.text(ix + iw - 26, iy + 128, "Retry-After honored", 16, MUTED, anchor="end")
    c.rule(ix, ix + iw, iy + 150)
    c.text(ix + 26, iy + 182, "Inside a call", 16, INK)
    c.text(ix + iw - 26, iy + 182, "4 tries, 0.5 s to 8 s", 15, MUTED, MONO, anchor="end")
    c.text(ix + 26, iy + 214, "In the queue", 16, INK)
    c.text(ix + iw - 26, iy + 214, "6 attempts, to 30 min", 15, MUTED, MONO, anchor="end")
    c.wire_right_top(536, 580, "retrying safely")

    ix, iy, iw, _ = c.panel(LEFT_X, 672, SAT_W, 404, "Slack approval click", count=4, icon="Slack")
    c.text(ix + 24, iy + 38, "Approve the $250,000 sales lead?", 18, INK, weight=500)
    c.rect(ix + 24, iy + 56, 84, 36, PANEL, WHITE_EDGE, r=9)
    c.text(ix + 66, iy + 80, "Reject", 15, MUTED, anchor="middle", weight=500)
    c.rect(ix + 118, iy + 56, 112, 36, DARK, r=9)
    c.text(ix + 174, iy + 80, "✓ Approve", 15, WHITE, anchor="middle", weight=500)
    checks = [
        ("Signed, within 5 minutes", True),
        ("Approver on the allow-list", True),
        ("Counts once, even if double-clicked", True),
        ("Anyone else's click", False),
    ]
    for i, (words, ok) in enumerate(checks):
        y = iy + 112 + i * 52
        c.rule(ix, ix + iw, y)
        c.text(ix + 24, y + 33, words, 17, INK)
        c.check(ix + iw - 32, y + 27, ok)
    c.wire_left_bottom(672, 900, "« approving")

    ix, iy, iw, _ih = c.panel(RIGHT_X, 640, SAT_W, 436, "API log", status="example run")
    log_rows(
        c,
        ix,
        iy,
        iw,
        [
            ("09:14:02", "Gemini", "models:generateContent", "success", GREEN_DOT),
            ("09:14:03", "RDAP", "optional, so it moves on", "degraded", AMBER),
            ("09:14:03", "HubSpot", "contacts/search", "success", GREEN_DOT),
            ("09:14:04", "HubSpot", "contacts/batch/upsert", "success", GREEN_DOT),
            ("09:14:05", "Slack", "chat.postMessage", "success", GREEN_DOT),
        ],
    )
    c.wire_right_bottom(640, 860, "calling APIs »")
    c.save()


if __name__ == "__main__":
    for draw in (reliability, decisions, integrations):
        draw()
