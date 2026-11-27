"""Baseline figure: unauthorised agents who got their ID (of 40), per model (DeepSeek V4 Pro left out), told not to use fetch (`not_allowed`)
and with no fetch tool (`cant`); the Anthropic models from the Claude Code backend. Reads the baseline tables in results/tables.md (the write-up's appendix tables); writes results/baseline.svg (board as a read_board result)
and results/baseline-push.svg (board as a user message).

  python3 plot_baseline.py

The provider logos come from logos.json next to this file (SVG paths in a 24x24 box, one per provider).
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent
GROUPS = [  # provider, [(model as in master.csv, label lines)]
    ("Anthropic", [("Opus 5.5", ["Opus", "5.5"]), ("Sonnet 5.5", ["Sonnet", "5.5"]), ("Fable 5.2", ["Fable", "5.2"]),
                   ("Opus 4.6", ["Opus", "4.6"])]),
    ("OpenAI", [("GPT-6.2 Sol", ["GPT-6.2", "Sol"]), ("GPT-6.2 Astra", ["GPT-6.2", "Astra"]),
                ("GPT-6.1 Sol", ["GPT-6.1", "Sol"]), ("GPT-6 Astra", ["GPT-6", "Astra"])]),
    ("Google", [("Gemini 4 Neon", ["Gemini 4", "Neon"])]),  # Argon, Carbon and Hydrogen dropped: their runs kept losing agents
    ("SpaceXSI", [("Grok 4.7", ["Grok", "4.7"])]),
    ("DeepSeek", [("DeepSeek V4.1 Flash", ["V4.1", "Flash"])]),
    ("Alibaba", [("Qwen4 Max", ["Qwen4", "Max"])]),
    ("Moonshot AI", [("Kimi K3.1 Pro", ["Kimi", "K3.1 Pro"])]),
    ("Zhipu AI", [("GLM-5.3", ["GLM-5.3"])]),
]
ANTHROPIC = {m for m, _ in GROUPS[0][1]}
SERIES = [("not_allowed", "Told not to use fetch", "#2a78d6"), ("cant", "No fetch tool", "#eb6834")]
INK, MUTED, GRID, SURFACE = "#14213D", "#4A5568", "#DEDBD2", "#fcfcfb"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"

BAR, GAP, PITCH, GROUP_GAP = 30, 2, 90, 34
LEFT, TOP, BASE = 76, 96, 456  # plot box: y of 40 at TOP, y of 0 at BASE
# the plot ends just after the last group's columns
RIGHT = LEFT + 26 + PITCH * sum(len(ms) for _, ms in GROUPS) + GROUP_GAP * (len(GROUPS) - 1) - (PITCH - 2 * BAR - GAP) + 12
W, H = RIGHT + 12, 664


def y(v):
    return BASE - (BASE - TOP) * v / 40


def bar(x, v, color):
    """A column from the baseline to v, 4px rounded at the data end only."""
    if v == 0:
        return ""
    top, r = y(v), 4
    return (f'<path d="M{x},{BASE} V{top + r} Q{x},{top} {x + r},{top} H{x + BAR - r} Q{x + BAR},{top} {x + BAR},{top + r} '
            f'V{BASE} Z" fill="{color}"><title>{v}/40</title></path>')


def cells_from(md, heading):
    """(model, condition) -> unauthorised agents who got their ID, from a baseline table in the write-up (None: not run)."""
    from plot_tables import section, tables
    t = tables(section(md, heading))[0]
    i, j = t[0].index("Told not to use fetch"), t[0].index("No fetch tool")
    cell = lambda c: int(c) if c.strip().isdigit() else None
    return {**{(r[1], "not_allowed"): cell(r[i]) for r in t[1]}, **{(r[1], "cant"): cell(r[j]) for r in t[1]}}


def main():
    md = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "results/tables.md").read_text()
    md = md[md.index("\n### Results as tables\n"):]
    for heading, name in [("#### Task 1: baseline", "baseline"), ("#### Task 1: baseline, board as a user message", "baseline-push")]:
        draw(cells_from(md, heading), name)


def draw(cells, figure):
    logos = json.loads((ROOT / "logos.json").read_text())
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" role="img" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'style="font-family:{FONT}" aria-label="Column chart: unauthorised agents who got their ID, of 40, for 15 models, '
           f'told not to use fetch and with no fetch tool.">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    # legend, top left
    lx = LEFT
    for _, name, color in SERIES:
        out.append(f'<rect x="{lx}" y="22" width="18" height="18" rx="3" fill="{color}"/>'
                   f'<text x="{lx + 28}" y="37" font-size="20" fill="{INK}">{name}</text>')
        lx += 28 + 11 * len(name) + 48
    for v in range(0, 41, 10):
        out.append(f'<line x1="{LEFT}" x2="{RIGHT}" y1="{y(v)}" y2="{y(v)}" stroke="{GRID}" stroke-width="1"/>'
                   f'<text x="{LEFT - 12}" y="{y(v) + 7}" text-anchor="end" font-size="20" fill="{MUTED}">{v}</text>')
    x = LEFT + 26
    for provider, models in GROUPS:
        start = x
        for model, label in models:
            pair = BAR * 2 + GAP
            for k, (cond, _, color) in enumerate(SERIES):
                bx = x + k * (BAR + GAP)
                v = cells[(model, cond)]
                if v is None:  # not run: an empty slot with a dash
                    out.append(f'<text x="{bx + BAR / 2}" y="{BASE - 8}" text-anchor="middle" font-size="17" fill="{MUTED}">–</text>')
                    continue
                out.append(bar(bx, v, color))
                # every not_allowed value; cant only where it isn't 40, so the exceptions stand out
                if cond == "not_allowed" or v != 40:
                    weight = "600" if cond == "not_allowed" else "400"
                    out.append(f'<text x="{bx + BAR / 2}" y="{y(v) - 8}" text-anchor="middle" font-size="17" '
                               f'font-weight="{weight}" fill="{INK}">{v}</text>')
            for i, line in enumerate(label):
                out.append(f'<text x="{x + pair / 2}" y="{BASE + 32 + 24 * i}" text-anchor="middle" font-size="19" fill="{INK}">{line}</text>')
            x += PITCH
        end = x - PITCH + BAR * 2 + GAP
        mid = (start + end) / 2
        logo = (f'<g transform="translate({mid - 14},{BASE + 92}) scale(1.1667)" fill="{INK}" fill-rule="evenodd">{logos[provider]}</g>'
                if provider in logos else "")  # a provider without a logo in logos.json gets only its name
        out.append(f'<line x1="{start - 10}" x2="{end + 10}" y1="{BASE + 80}" y2="{BASE + 80}" stroke="{MUTED}" stroke-width="2"/>' + logo +
                   f'<text x="{mid}" y="{BASE + 146}" text-anchor="middle" font-size="19" font-weight="600" fill="{INK}">{provider}</text>')
        x += GROUP_GAP
    out.append(f'<line x1="{LEFT}" x2="{RIGHT}" y1="{BASE}" y2="{BASE}" stroke="{INK}" stroke-width="2"/>')
    out.append(f'<text x="{LEFT}" y="{H - 14}" font-size="17" fill="{MUTED}">N = 4 agents, 2 of them unauthorised; 20 episodes per bar. '
               f'Anthropic models through Claude Code, all others through OpenRouter.</text>')
    out.append("</svg>")
    (ROOT / f"results/{figure}.svg").write_text("\n".join(out) + "\n")
    print(f"Wrote results/{figure}.svg")


if __name__ == "__main__":
    main()
