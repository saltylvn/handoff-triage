"""Overview, workflow, architecture and reliability pages for docs/assets, plus the GitHub social
preview, in the same light canvas style as canvas.py. Run through scripts/render-diagrams.sh."""

from canvas import (
    ACCENT,
    ACCENT_INK,
    AMBER,
    DARK,
    GREEN,
    GREEN_DOT,
    INK,
    LEFT_X,
    MONO,
    MUTED,
    PANEL,
    PANEL_EDGE,
    RED_DOT,
    RIGHT_X,
    SAT_W,
    SOFT,
    TINT,
    URL,
    WHITE,
    WHITE_EDGE,
    Canvas,
    H,
    M,
    W,
    log_rows,
    text_width,
)

TOTAL = 8


class Slide(Canvas):
    def __init__(self, name, page, tag, headline, label, caption=None):
        self.name, self.label = name, label
        self.back, self.front = [], []
        self.rect(M, 40, text_width(tag, 15, True) + 32, 34, "none", PANEL_EDGE, r=17)
        self.text(M + 16, 62, tag, 15, MUTED, MONO)
        self.text(W - M, 64, "Human-in-the-Loop Triage", 20, MUTED, anchor="end", weight=500)
        for i, (words, color) in enumerate(headline):
            self.text(M, 132 + i * 58, words, 52, color, weight=500, spacing=-1.5)
        if caption:
            self.text(W / 2, 1118, caption.upper(), 16, MUTED, MONO, anchor="middle", spacing=5)
        self.text(M, H - 36, f"Tyler Clark  ·  {URL}", 18, MUTED)
        if page:
            self.text(W - M, H - 36, f"{page} / {TOTAL}", 16, MUTED, MONO, anchor="end")

    def link(self, points, label=None, at=None):
        d = "M " + " L ".join(f"{x} {y}" for x, y in points)
        self.back.append(
            f'<path d="{d}" fill="none" stroke="#c4bfba" stroke-width="1.5" stroke-dasharray="5 5"/>'
        )
        for x, y in (points[0], points[-1]):
            self.back.append(
                f'<circle cx="{x}" cy="{y}" r="6" fill="#f3f2f1" stroke="#c4bfba" stroke-width="1.5"/>'
            )
        if label:
            self.pill_label(*at, label)

    def lines(self, x, y, rows, size, fill=MUTED, gap=None, **kw):
        gap = gap or round(size * 1.4)
        for i, row in enumerate(rows):
            self.text(x, y + i * gap, row, size, fill, **kw)


def run_badge(c, x_right, y, words, ok=True):
    """An n8n-style run badge: a pill with a green check (or a red cross) and a short result."""
    w = text_width(words, 13, True) + 46
    x = x_right - w
    c.rect(x, y - 15, w, 30, WHITE, WHITE_EDGE, r=15)
    if ok:
        c.front.append(
            f'<path d="M {x + 13} {y} L {x + 17} {y + 4} L {x + 24} {y - 5}" fill="none" stroke="{GREEN}" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    else:
        c.front.append(
            f'<path d="M {x + 14} {y - 5} L {x + 23} {y + 4} M {x + 23} {y - 5} L {x + 14} {y + 4}" '
            f'stroke="{RED_DOT}" stroke-width="2" stroke-linecap="round"/>'
        )
    c.text(x + 32, y + 5, words, 13, INK, MONO)
    return w


def code_lines(c, x, y, rows, size=15, gap=24):
    """Mono code with simple coloring: keys accent, strings ink, comments soft."""
    for i, row in enumerate(rows):
        parts = row if isinstance(row, list) else [(row, INK)]
        cx = x
        for words, color in parts:
            c.text(cx, y + i * gap, words, size, color, MONO)
            cx += text_width(words, size, True)


def approval_card(c, ix, iy, iw):
    c.text(ix + 24, iy + 42, "Sales lead, $250,000 budget", 21, INK, weight=500)
    c.text(ix + 24, iy + 70, "Held for a person at confidence 1.0", 16, SOFT)
    c.chip(ix + 24, iy + 88, "high_value", 13, fill=TINT, edge=ACCENT, color=ACCENT_INK)
    c.rect(ix + 24, iy + 136, 92, 40, PANEL, WHITE_EDGE, r=10)
    c.text(ix + 70, iy + 162, "Reject", 17, MUTED, anchor="middle", weight=500)
    c.rect(ix + 128, iy + 136, 124, 40, DARK, r=10)
    c.text(ix + 190, iy + 162, "✓ Approve", 17, WHITE, anchor="middle", weight=500)


def overview(name, page=None):
    c = Slide(
        name,
        page,
        "Human-in-the-loop AI workflow",
        [("Automates the routine.", INK), ("Asks a person about the rest.", SOFT)],
        "A contact form message is read by AI, checked by rules in code, then handled alone or approved by a person, "
        "and HubSpot and Slack are updated. On 70 held-out synthetic messages: 84.3 percent handled alone, 96.6 percent "
        "correct when alone, all 4 sensitive messages sent to a person, and $0.33 model cost per 1,000.",
        caption="Human-in-the-loop workflow",
    )
    c.hub("ai reads. code decides. a person approves.")

    ix, iy, iw, _ = c.panel(LEFT_X, 236, SAT_W, 336, "Workflow", count=6)
    steps = [
        ("Receive", "signed webhook"),
        ("Classify", "Gemini, checked JSON"),
        ("Enrich", "domain age, CRM lookup"),
        ("Route", "rules in code"),
        ("Act", "HubSpot and Slack"),
        ("Log", "every decision, append-only"),
    ]
    for i, (title, words) in enumerate(steps):
        y = iy + i * 44
        if i:
            c.rule(ix, ix + iw, y)
        c.text(ix + 22, y + 29, str(i + 1), 14, SOFT, MONO)
        c.text(ix + 46, y + 29, title, 17, ACCENT_INK if title == "Route" else INK, weight=500)
        c.text(ix + iw - 22, y + 29, words, 15, MUTED, anchor="end")
    c.wire_left_top(572, 610, "running steps")

    ix, iy, iw, _ = c.panel(RIGHT_X, 236, SAT_W, 342, "Results", status="70 held out, synthetic")
    c.text(ix + 26, iy + 62, "84.3%", 44, INK, weight=500, spacing=-1)
    c.text(ix + 26 + text_width("84.3%", 44) + 16, iy + 62, "handled alone", 20, SOFT)
    c.rect(ix + 26, iy + 86, iw - 52, 10, PANEL, r=5)
    c.rect(ix + 26, iy + 86, (iw - 52) * 0.843, 10, DARK, r=5)
    c.text(ix + 26, iy + 124, "59 of 70 messages", 16, MUTED)
    c.text(ix + iw - 26, iy + 124, "no person needed", 16, MUTED, anchor="end")
    c.rule(ix, ix + iw, iy + 146)
    for i, (label, value) in enumerate(
        (
            ("Correct when alone", "96.6%"),
            ("Sensitive, sent to a person", "4 of 4"),
            ("Model cost per 1,000", "$0.33"),
        )
    ):
        y = iy + 180 + i * 34
        c.text(ix + 26, y, label, 17, INK)
        c.text(ix + iw - 26, y, value, 18, INK, anchor="end", weight=500)
    c.wire_right_top(578, 610, "measuring »")

    ix, iy, iw, _ = c.panel(
        LEFT_X,
        680,
        SAT_W,
        322,
        "Approval request",
        status="Pending",
        status_color=AMBER,
        icon="Slack",
    )
    approval_card(c, ix, iy, iw)
    c.rule(ix, ix + iw, iy + 200)
    c.text(ix + 24, iy + 232, "Tested live in Slack with a real click", 16, SOFT)
    c.wire_left_bottom(680, 900, "« asking a person")

    ix, iy, iw, _ih = c.panel(RIGHT_X, 640, SAT_W, 330, "Built with", count=12)
    rows = [
        ["Python", "FastAPI", "Pydantic", "SQLite"],
        ["Gemini API", "HubSpot OAuth 2.0"],
        ["Slack API", "Signed webhooks", "RDAP"],
        ["Docker", "GitHub Actions", "Claude Code"],
    ]
    for r, row in enumerate(rows):
        cx = ix + 22
        for chip in row:
            ic = next((n for n in ("Gemini", "HubSpot", "Slack") if chip.startswith(n)), None)
            cx += c.chip(cx, iy + 22 + r * 44, chip, 14, h=32, icon=ic) + 10
    c.rule(ix, ix + iw, iy + 204)
    c.text(ix + 22, iy + 236, "83 tests · 95% coverage · CI on every push", 14, SOFT, MONO)
    c.wire_right_bottom(640, 860, "built with")
    c.save()


def workflow(name):
    c = Slide(
        name,
        None,
        "Automation workflow",
        [("The AI supplies the facts.", INK), ("Code decides what happens.", SOFT)],
        "Six workflow steps from signed webhook to audit log, and the seven conditions that send a message to a person.",
    )
    steps = [
        ("Receive", "Verify the signed webhook, then queue it"),
        ("Classify", "Gemini returns schema-checked JSON"),
        ("Enrich", "Domain age, plus a CRM contact lookup"),
        ("Route", "Plain rules choose: act alone or ask"),
        ("Act", "Update HubSpot and post to Slack"),
        ("Log", "Record each decision, append-only"),
    ]
    flows = ["queued", "facts", "enriched", "plan", "result"]
    tools = [["Form"], ["Gemini"], ["RDAP", "HubSpot"], [], ["HubSpot", "Slack"], []]
    badges = ["202 accepted", "valid JSON", "2 lookups", "act alone", "upserted, posted", "logged"]
    x, w, h, gap = M, 640, 92, 42
    for i, (title, detail) in enumerate(steps):
        y = 236 + i * (h + gap)
        on = title == "Route"
        c.rect(x, y, w, h, TINT if on else WHITE, ACCENT if on else WHITE_EDGE, r=20, shadow=True)
        c.front.append(
            f'<circle cx="{x + 46}" cy="{y + h / 2}" r="20" fill="{WHITE if on else PANEL}" '
            f'stroke="{ACCENT if on else WHITE_EDGE}" stroke-width="1.2"/>'
        )
        c.text(
            x + 46, y + h / 2 + 6, str(i + 1), 16, ACCENT_INK if on else INK, MONO, anchor="middle"
        )
        c.text(x + 86, y + 40, title, 22, ACCENT_INK if on else INK, weight=500)
        c.text(x + 86, y + 66, detail, 17, MUTED)
        bw = run_badge(c, x + w - 20, y + h / 2, badges[i])
        tx = x + w - 20 - bw - 12
        for name in reversed(tools[i]):
            tx -= 34
            c.rect(tx, y + h / 2 - 15, 30, 30, PANEL, WHITE_EDGE, r=9)
            c.icon(name, tx + 6, y + h / 2 - 9, 18)
        if i < 5:
            c.link(
                [(x + w / 2, y + h), (x + w / 2, y + h + gap)],
                flows[i],
                (x + w / 2, y + h + gap / 2),
            )
    px, pw = 760, W - M - 760
    ix, iy, iw, _ = c.panel(
        px, 236, pw, 616, "A person approves when", count=7, status="otherwise it runs alone"
    )
    rules = [
        "Model confidence is below 0.90",
        "The AI's reply is invalid",
        "A legal, security or data-deletion issue",
        "A team of 500+ or a budget of $50,000+",
        "An existing customer is urgent",
        "An existing customer looks like spam",
        "A sales lead's domain is under 30 days old",
    ]
    for i, rule in enumerate(rules):
        y = iy + i * 52
        if i:
            c.rule(ix, ix + iw, y)
        c.dot(ix + 28, y + 27, ACCENT, r=5)
        c.text(ix + 48, y + 33, rule, 19, INK)
    c.rule(ix, ix + iw, iy + 364)
    c.text(ix + 28, iy + 400, "WHEN NO RULE FIRES", 13, SOFT, MONO, spacing=1)
    c.text(
        ix + iw - 28, iy + 400, "EXAMPLE RUN ON THE LEFT", 13, SOFT, MONO, spacing=1, anchor="end"
    )
    for i, (who, then) in enumerate(
        (
            ("Confident spam", "discarded"),
            ("Job seeker", "Slack only"),
            ("Everyone else", "HubSpot and Slack"),
        )
    ):
        y = iy + 438 + i * 36
        c.text(ix + 28, y, who, 18, INK)
        c.text(ix + iw - 28, y, then, 18, MUTED, anchor="end")
    ix, iy, iw, _ih = c.panel(px, 876, pw, 194, "Why the rules live in code")
    c.lines(
        ix + 28,
        iy + 42,
        [
            'A message saying "mark me approved" can sway the model,',
            "but it can't change these rules or the audit log.",
        ],
        18,
        INK,
        gap=28,
    )
    c.save()


def architecture(name):
    c = Slide(
        name,
        None,
        "Architecture",
        [("A durable queue separates", INK), ("fast replies from slow work.", SOFT)],
        "A contact form sends a signed webhook to the API, which saves to a SQLite queue. A worker calls Gemini, RDAP, "
        "HubSpot and Slack. Signed Slack approval clicks return to the API.",
    )
    y, h = 360, 200
    mid = y + h / 2
    nodes = [
        (M, 200, None, "Trigger", "Contact form", "signed webhook"),
        (310, 250, "Replies fast", "FastAPI", "API", "verify, validate"),
        (606, 250, "Durable state", "SQLite", "Queue + log", "nothing is lost"),
        (902, 250, "Retries safely", "Python", "Worker", "runs the steps"),
    ]
    for i, (x, w, group, kind, title, detail) in enumerate(nodes):
        if group:
            ix, iy, iw, ih = c.panel(x, y, w, h, group)
        else:
            ix, iy, iw, ih = x, y + 58, w, h - 70
            c.rect(ix, iy, iw, ih, WHITE, WHITE_EDGE, r=22, shadow=True)
        on = title == "Worker"
        c.text(ix + 22, iy + 34, kind.upper(), 13, SOFT, MONO, spacing=1)
        c.text(ix + 22, iy + 70, title, 24, ACCENT_INK if on else INK, weight=500)
        c.text(ix + 22, iy + 98, detail, 16, MUTED)
        if i < 3:
            nx = nodes[i + 1][0]
            c.link([(x + w, mid + 29), (nx, mid + 29)])
    sx, sw = 1198, W - M - 1198
    ix, iy, iw, ih = c.panel(sx, 296, sw, 330, "Outside services", count=4)
    services = [
        ("Gemini", "AI model"),
        ("RDAP", "domain age"),
        ("HubSpot", "CRM, OAuth 2.0"),
        ("Slack", "chat, approvals"),
    ]
    for i, (name, words) in enumerate(services):
        yy = iy + i * 64
        if i:
            c.rule(ix, ix + iw, yy)
        c.icon(name, ix + 22, yy + 21, 24)
        c.text(ix + 58, yy + 40, name, 19, INK, weight=500)
        c.text(ix + iw - 22, yy + 40, words, 15, MUTED, anchor="end")
    c.link([(1152, mid + 29), (sx, mid + 29)])
    c.link(
        [(sx + sw / 2, 626), (sx + sw / 2, 676), (435, 676), (435, y + h)],
        "signed approval click",
        (800, 676),
    )
    ix, iy, iw, ih = c.panel(M, 730, 900, 370, "Webhook call", status="example values")
    c.text(ix + 24, iy + 38, "REQUEST", 12, SOFT, MONO, spacing=1)
    code_lines(
        c,
        ix + 24,
        iy + 66,
        [
            [("POST ", ACCENT_INK), ("/webhooks/inbound", INK)],
            [("x-timestamp: ", ACCENT_INK), ("1793908800", INK)],
            [("x-signature: ", ACCENT_INK), ("v0=3f9a…c41e", INK), ("   # HMAC-SHA256", SOFT)],
            [
                ('{"event_id": ', ACCENT_INK),
                ('"evt_1042", ', INK),
                ('"email": ', ACCENT_INK),
                ('"dana@example.com",', INK),
            ],
            [(' "message": ', ACCENT_INK), ('"Pricing for 600 seats?"}', INK)],
        ],
        15,
        25,
    )
    c.rule(ix, ix + iw, iy + 192)
    c.text(ix + 24, iy + 226, "RESPONSE", 12, SOFT, MONO, spacing=1)
    c.status(ix + 190, iy + 222, "202", GREEN_DOT, 14)
    code_lines(
        c,
        ix + 210,
        iy + 228,
        [
            [
                ('{"id": ', ACCENT_INK),
                ('"7f3c…", ', INK),
                ('"duplicate": ', ACCENT_INK),
                ("false}", INK),
                ("   # first delivery", SOFT),
            ]
        ],
        15,
    )
    c.status(ix + 190, iy + 262, "202", GREEN_DOT, 14)
    code_lines(
        c,
        ix + 210,
        iy + 268,
        [
            [
                ('{"id": ', ACCENT_INK),
                ('"7f3c…", ', INK),
                ('"duplicate": ', ACCENT_INK),
                ("true}", INK),
                ("    # same event again", SOFT),
            ]
        ],
        15,
    )
    notes = [
        ("Nothing is lost", "Saved before the 202 is sent"),
        ("Nothing repeats", "A step ledger skips finished work"),
        ("Room to grow", "All SQL in one module, for Postgres"),
    ]
    ix, iy, iw, ih = c.panel(988, 730, W - M - 988, 370, "Why it's built this way", count=3)
    for i, (title, words) in enumerate(notes):
        y = iy + i * 100
        if i:
            c.rule(ix, ix + iw, y)
        c.text(ix + 24, y + 36, title, 19, INK, weight=500)
        c.text(ix + 24, y + 62, words, 16, MUTED)
    c.save()


def reliability(name):
    c = Slide(
        name,
        None,
        "Reliability",
        [("One record and one message,", INK), ("even when things fail.", SOFT)],
        "Six failure scenarios and how the system responds, tested with injected faults and a live webhook replay, "
        "and an example retry timeline: a 503, then a 429 with Retry-After, then success.",
    )
    ix, iy, iw, _ = c.panel(
        M,
        236,
        W - 2 * M,
        552,
        "Failure scenarios",
        count=6,
        status="83 automated tests, injected faults",
        status_color=GREEN_DOT,
    )
    c.text(ix + 28, iy + 40, "IF THIS HAPPENS", 13, SOFT, MONO, spacing=1)
    c.text(ix + 740, iy + 40, "THE SYSTEM", 13, SOFT, MONO, spacing=1)
    rows = [
        ("The same webhook arrives twice", "A unique key ignores the copy"),
        ("The worker crashes midway", "It resumes at the unfinished step"),
        ("HubSpot's reply gets lost", "Upsert updates the same contact"),
        ("Slack's reply gets lost", "It finds the earlier post first"),
        ("An approver double-clicks", "Only the first click counts"),
        ("An item keeps failing", "It's set aside, with a Slack alert"),
    ]
    for i, (problem, answer) in enumerate(rows):
        top = iy + 58 + i * 70
        c.rule(ix, ix + iw, top)
        c.text(ix + 28, top + 43, problem, 22, MUTED)
        c.link([(ix + 600, top + 36), (ix + 712, top + 36)])
        c.text(ix + 740, top + 43, answer, 22, INK, weight=500)
        c.check(ix + iw - 40, top + 36)

    ix, iy, iw, _ih = c.panel(
        M,
        812,
        W - 2 * M,
        270,
        "Retry timeline",
        icon="HubSpot",
        status="example: HubSpot under load",
    )
    x0, x1, ay = ix + 60, ix + iw - 90, iy + 72
    c.front.append(
        f'<line x1="{x0}" y1="{ay}" x2="{x1}" y2="{ay}" stroke="#e7e5e4" stroke-width="2"/>'
    )
    events = [
        (0.00, False, "attempt 1", "503 Service Unavailable"),
        (0.30, False, "attempt 2", "429 Too Many Requests"),
        (0.82, True, "attempt 3", "200 OK, contact upserted"),
    ]
    for frac, ok, title, words in events:
        ex = x0 + frac * (x1 - x0)
        color = GREEN_DOT if ok else RED_DOT
        c.front.append(
            f'<circle cx="{ex:.1f}" cy="{ay}" r="10" fill="{WHITE}" stroke="{color}" stroke-width="2.5"/>'
        )
        c.dot(ex, ay, color, r=4)
        c.text(ex, ay - 26, title, 14, SOFT, MONO, anchor="middle" if frac else None)
        c.text(
            ex if frac else ex - 10,
            ay + 40,
            words,
            16,
            INK,
            weight=500,
            anchor="middle" if frac else None,
        )
    for a, b, label in (
        (0.0, 0.30, "backoff with jitter, up to 0.5 s"),
        (0.30, 0.82, "waits the 2 s that Retry-After asked for"),
    ):
        mx = x0 + (a + b) / 2 * (x1 - x0)
        c.pill_label(mx, ay, label)
    c.rule(ix, ix + iw, iy + 136)
    c.text(
        ix + 24,
        iy + 172,
        "Inside a call: 4 tries, 0.5 s doubling to 8 s with full jitter. A wait over 15 s goes back to the queue instead.",
        16,
        MUTED,
    )
    c.save()


def social_preview():
    """GitHub's repository preview: exactly 1280 by 640."""
    sw, sh = 1280, 640
    c = Canvas.__new__(Canvas)
    c.name = "social-preview"
    c.label = (
        "Human-in-the-Loop Triage: AI reads, code decides, a person approves. Built with Gemini, "
        "HubSpot, Slack, Python and FastAPI. 84.3 percent handled alone and 96.6 percent correct "
        "on 70 held-out synthetic messages."
    )
    c.back, c.front = [], []
    tag = "Human-in-the-loop AI workflow"
    c.rect(56, 52, text_width(tag, 15, True) + 32, 34, "none", PANEL_EDGE, r=17)
    c.text(72, 74, tag, 15, MUTED, MONO)
    c.text(56, 176, "Human-in-the-Loop", 62, INK, weight=500, spacing=-1.8)
    c.text(56, 244, "Triage", 62, INK, weight=500, spacing=-1.8)
    c.text(56, 298, "AI reads. Code decides. A person approves.", 25, SOFT, weight=500)
    cx = 56
    for name in ("Gemini", "HubSpot", "Slack"):
        cx += c.chip(cx, 330, name, 16, h=38, icon=name) + 10
    for name in ("Python", "FastAPI"):
        cx += c.chip(cx, 330, name, 16, h=38) + 10
    stats = (
        ("84.3%", "handled alone"),
        ("96.6%", "correct alone"),
        ("4 of 4", "sensitive to a person"),
    )
    sx = 56
    for value, words in stats:
        c.text(sx, 452, value, 38, INK, weight=500, spacing=-1)
        c.text(sx, 480, words, 15, MUTED)
        sx += 200
    c.text(56, 512, "70 HELD-OUT SYNTHETIC MESSAGES", 12, SOFT, MONO, spacing=1.2)
    c.text(56, 596, URL, 17, MUTED)

    px, pw = 744, 480
    ix, iy, iw, _ = c.panel(
        px, 52, pw, 300, "Approval request", status="Pending", status_color=AMBER, icon="Slack"
    )
    approval_card(c, ix, iy, iw)
    ix, iy, iw, _ih = c.panel(px, 376, pw, 228, "API log", status="example run")
    log_rows(
        c,
        ix,
        iy,
        iw,
        [
            ("09:14:02", "Gemini", "models:generateContent", "success", GREEN_DOT),
            ("09:14:04", "HubSpot", "contacts/batch/upsert", "success", GREEN_DOT),
        ],
        row_h=72,
        top=12,
    )
    c.save(size=(sw, sh))


if __name__ == "__main__":
    overview("overview", None)
    workflow("workflow")
    architecture("architecture")
    reliability("reliability")
    social_preview()
