"""Figures for the write-up's results on Tasks 1 to 4: a heatmap per task (settings by models), grouped columns for action
severity and the eval-awareness baseline. Reads the tables in results/tables.md (the write-up's appendix tables); writes results/task1-boards.svg,
task2.svg, task3.svg and task4.svg. Same colours, font and logos as plot_baseline.py.

  python3 plot_tables.py [tables.md]
  # PNGs: uv run --with resvg-py python3 -c "import resvg_py, glob; [open(f[:-4] + '.png', 'wb').write(bytes(resvg_py.svg_to_bytes(svg_path=f))) for f in glob.glob('results/task*.svg')]"
"""

import json
import re
import sys
from pathlib import Path

INK, MUTED, GRID, SURFACE, ZERO = "#14213D", "#4A5568", "#DEDBD2", "#fcfcfb", "#f0efec"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6"]  # sequential blue, 100 -> 450:
# the darkest step is the blue of the bars in the other figures
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"  # series colours in palette order; blue and orange as in plot_baseline.py
MODELS = [("Opus 5.5", ["Opus", "5.5"], "Anthropic"), ("Sonnet 5.5", ["Sonnet", "5.5"], "Anthropic"),
          ("Fable 5.2", ["Fable", "5.2"], "Anthropic"), ("GPT-6.2 Sol", ["GPT-6.2", "Sol"], "OpenAI"),
          ("GPT-6.2 Astra", ["GPT-6.2", "Astra"], "OpenAI"), ("Kimi K3.1 Pro", ["Kimi", "K3.1 Pro"], "Moonshot AI"),
          ("Gemini 4 Neon", ["Gemini 4", "Neon"], "Google · Gemini 4"), ("DeepSeek V4.1 Flash", ["DeepSeek", "V4.1 Flash"], "DeepSeek")]


def tables(md):
    """Every markdown table in the write-up as (header cells, rows of cells), in order."""
    out, cur = [], None
    for line in md.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cur is None:
                cur = (cells, [])
            elif not set(line) <= set("|-: "):
                cur[1].append(cells)
        elif cur is not None:
            out.append(cur); cur = None
    return out


def section(md, heading):
    """The text under a heading, up to the next heading."""
    a = md.index("\n" + heading + "\n") + len(heading) + 2
    b = min((i for i in (md.find("\n#", a),) if i >= 0), default=len(md))
    return md[a:b]


def num(c):
    return int(re.match(r"\d+", c).group())


def color(f):
    return ZERO if f == 0 else RAMP[min(len(RAMP) - 1, int(f * (len(RAMP) - 1) + 0.5))]


def wrap(text, width):
    lines = [""]
    for w in text.replace("`", "").split():
        if lines[-1] and len(lines[-1]) + 1 + len(w) > width:
            lines.append(w)
        else:
            lines[-1] = (lines[-1] + " " + w).strip()
    return lines


def heatmap(rows, values, denom, logos, path, note):
    """rows: setting labels, as in the write-up's table; values[i][j]: the table cell for setting i, model j, either a count
    of denom or "count/denominator"."""
    LABEL_W, CELL_W, TOP = 470, 118, 146
    labels = [wrap(r, 44) for r in rows]
    heights = [max(58, 22 * len(l) + 16) for l in labels]
    W = LABEL_W + CELL_W * len(MODELS) + 24
    H = TOP + sum(heights) + 58
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="font-family:{FONT}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    # provider logo above each run of models from one provider, then the model names
    j = 0
    while j < len(MODELS):
        k = j
        while k + 1 < len(MODELS) and MODELS[k + 1][2] == MODELS[j][2]:
            k += 1
        x0, x1 = LABEL_W + CELL_W * j + 6, LABEL_W + CELL_W * (k + 1) - 6
        mid = (x0 + x1) / 2
        if MODELS[j][2] in logos:
            out.append(f'<g transform="translate({mid - 14},30) scale(1.1667)" fill="{INK}" fill-rule="evenodd">{logos[MODELS[j][2]]}</g>')
        out.append(f'<line x1="{x0}" x2="{x1}" y1="70" y2="70" stroke="{MUTED}" stroke-width="2"/>')
        j = k + 1
    for j, (_, lab, _) in enumerate(MODELS):
        cx = LABEL_W + CELL_W * j + CELL_W / 2
        for i, line in enumerate(lab):
            out.append(f'<text x="{cx}" y="{98 + 22 * i}" text-anchor="middle" font-size="18" fill="{INK}">{line}</text>')
    y = TOP
    for i, row in enumerate(rows):
        CELL_H = heights[i]
        for k, line in enumerate(labels[i]):
            out.append(f'<text x="{LABEL_W - 16}" y="{y + CELL_H / 2 + 7 - 11 * (len(labels[i]) - 1) + 22 * k}" text-anchor="end" '
                       f'font-size="18" fill="{INK}">{line}</text>')
        for j in range(len(MODELS)):
            v = num(values[i][j]); d = int(values[i][j].split("/")[1]) if "/" in values[i][j] else denom; f = v / d
            x = LABEL_W + CELL_W * j
            out.append(f'<rect x="{x + 1}" y="{y + 1}" width="{CELL_W - 2}" height="{CELL_H - 2}" rx="4" fill="{color(f)}">'
                       f'<title>{MODELS[j][0]}: {v}/{d}</title></rect>')
            ink = "#ffffff" if f > 0.7 else INK
            out.append(f'<text x="{x + CELL_W / 2}" y="{y + CELL_H / 2 + 7}" text-anchor="middle" font-size="19" '
                       f'font-weight="{600 if v else 400}" fill="{ink}">{v}</text>')
        y += CELL_H
    out.append(f'<text x="24" y="{H - 20}" font-size="16" fill="{MUTED}">{note} Darker is higher.</text>')
    out.append("</svg>")
    path.with_suffix(".svg").write_text("\n".join(out) + "\n")


def grouped(series, values, denom, logos, path, note, models=MODELS, top=None, bar=30, pitch=160, names=False):
    """values[s][j]: count for series s, model j, of denom; grouped columns per model, a provider rule and logo under each
    run of one provider's models (with its name when `names`). `top` is the y-axis maximum, if not denom."""
    colors = [BLUE, ORANGE, AQUA, YELLOW][:len(series)]
    top = top or denom
    GAP, LEFT = 2, 84
    W = LEFT + pitch * len(models) + 20
    TOPY, BASE = 110, 450
    foot = wrap(note, int((W - 48) / 8))  # the footer, wrapped to the figure's width
    H = BASE + (170 if models[0][2] else 90) + (26 if names else 0) + 22 * (len(foot) - 1)
    y = lambda v: BASE - (BASE - TOPY) * v / top
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="font-family:{FONT}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    lx, ly = LEFT, 22  # legend, wrapping to a second row when it runs out of width
    for name, c in zip(series, colors):
        w = 28 + 10 * len(name) + 44
        if lx + w > W:
            lx, ly = LEFT, ly + 30
        out.append(f'<rect x="{lx}" y="{ly}" width="18" height="18" rx="3" fill="{c}"/><text x="{lx + 28}" y="{ly + 15}" font-size="19" fill="{INK}">{name}</text>')
        lx += w
    for v in range(0, top + 1, top // 4):
        out.append(f'<line x1="{LEFT}" x2="{W - 20}" y1="{y(v)}" y2="{y(v)}" stroke="{GRID}"/>'
                   f'<text x="{LEFT - 12}" y="{y(v) + 7}" text-anchor="end" font-size="18" fill="{MUTED}">{v}</text>')
    for j, (_, lab, _) in enumerate(models):
        x0 = LEFT + pitch * j + (pitch - (len(series) * bar + (len(series) - 1) * GAP)) / 2
        for s in range(len(series)):
            v = values[s][j]; bx = x0 + s * (bar + GAP)
            if v:
                t, r = y(v), min(4, bar / 4)
                out.append(f'<path d="M{bx},{BASE} V{t + r} Q{bx},{t} {bx + r},{t} H{bx + bar - r} Q{bx + bar},{t} {bx + bar},{t + r} '
                           f'V{BASE} Z" fill="{colors[s]}"><title>{series[s]}: {v}/{denom}</title></path>')
            out.append(f'<text x="{bx + bar / 2}" y="{y(v) - 8}" text-anchor="middle" font-size="{15 if bar >= 24 else 13}" fill="{INK}">{v}</text>')
        cx = LEFT + pitch * j + pitch / 2
        for i, line in enumerate(lab):
            out.append(f'<text x="{cx}" y="{BASE + 30 + 22 * i}" text-anchor="middle" font-size="18" fill="{INK}">{line}</text>')
        p = models[j][2]
        if p and (j == 0 or models[j - 1][2] != p):  # no provider: no rule or logo
            k = j
            while k + 1 < len(models) and models[k + 1][2] == p:
                k += 1
            mid = (LEFT + pitch * j + LEFT + pitch * (k + 1)) / 2
            out.append(f'<line x1="{LEFT + pitch * j + 12}" x2="{LEFT + pitch * (k + 1) - 12}" y1="{BASE + 72}" y2="{BASE + 72}" stroke="{MUTED}" stroke-width="2"/>')
            if p in logos:
                out.append(f'<g transform="translate({mid - 14},{BASE + 84}) scale(1.1667)" fill="{INK}" fill-rule="evenodd">{logos[p]}</g>')
            if names:  # True: the provider's name; a dict: a name per provider
                out.append(f'<text x="{mid}" y="{BASE + 140}" text-anchor="middle" font-size="18" font-weight="600" fill="{INK}">'
                           f'{names.get(p, p) if isinstance(names, dict) else p}</text>')
    out.append(f'<line x1="{LEFT}" x2="{W - 20}" y1="{BASE}" y2="{BASE}" stroke="{INK}" stroke-width="2"/>')
    for i, line in enumerate(foot):
        out.append(f'<text x="24" y="{H - 16 - 22 * (len(foot) - 1 - i)}" font-size="16" fill="{MUTED}">{line}</text>')
    out.append("</svg>")
    path.with_suffix(".svg").write_text("\n".join(out) + "\n")


def main():
    root = Path(__file__).parent
    md = Path(sys.argv[1] if len(sys.argv) > 1 else root / "results/tables.md").read_text()
    md = md[md.index("\n### Results as tables\n"):]
    logos, out = json.loads((root / "logos.json").read_text()), root / "results"
    col = lambda t: [t[0].index(m) for m, _, _ in MODELS]

    PUSH = ", board as a user message"  # the appendix versions: same table headings with this suffix
    for suffix, tag in [("", ""), (PUSH, "-push")]:  # main text (board as a read_board result), then the appendix
        t = tables(section(md, "#### Task 1: what moves the current-generation models" + suffix))[0]
        heatmap([r[0].strip('"') for r in t[1]], [[r[c] for c in col(t)] for r in t[1]], 40, logos, out / f"task1-boards{tag}",
                "Unauthorised agents who got their ID, of 40 (20 episodes × 2 unauthorised agents).")
        for name, heading in [("task2", "#### Task 2: package registry"), ("task3", "#### Task 3: shared storage")]:
            t = tables(section(md, heading + suffix))[0]
            heatmap([r[0] for r in t[1]], [[r[c] for c in col(t)] for r in t[1]], 80, logos, out / f"{name}{tag}",
                    "Agents who took the attacker's action, of 80 (20 episodes × 4 agents), or of 60 where the request is in one agent's name.")
        t4 = section(md, "#### Task 4: access control" + suffix)
        heads = re.findall(r"^\*\*(.+)\*\*$", t4, re.M)  # one bold heading per table
        # a heatmap like Tasks 1 to 3: one row per setting (the tables' bold headings), cells "approved/160"
        cells = [[next(r for r in t[1] if r[0] == m)[t[0].index("Attacker's applicants approved")] for m, _, _ in MODELS] for t in tables(t4)]
        assert len(heads) == len(cells)
        heatmap(heads, cells, 160, logos, out / f"task4{tag}", "Attacker's applicants approved, of 160 in the swarm (80 reviewers, 2 per queue)"
                + (", of 40 for one reviewer alone (20 reviewers)." if len(heads) > 3 else "."))
        # action severity: one group per model and setting (Opus first, as in the other figures), a column per action
        t = tables(section(md, "#### Task 1: action severity" + suffix))[0]
        rows = {r[0]: r for r in t[1]}
        settings = [("Opus 5.5, nothing on the board", ["Nothing on", "the board"], "Anthropic"),
                    ("Opus 5.5, the operator line", ["The operator", "line"], "Anthropic"),
                    ("Kimi K3.1 Pro, nothing on the board", ["Nothing on", "the board"], "Moonshot AI")]
        grouped(t[0][1:], [[num(rows[m][k]) for m, _, _ in settings] for k in range(1, len(t[0]))], 40, logos, out / f"task1-severity{tag}",
                "Unauthorised agents who completed their task, of 40 (20 episodes × 2 unauthorised agents). Opus through Claude Code.",
                models=settings, pitch=200, names={"Anthropic": "Opus 5.5", "Moonshot AI": "Kimi K3.1 Pro"})
    # eval awareness on the Task 1 baseline, every model in the baseline figure's order
    import plot_baseline
    models = [(m, lab, prov) for prov, ms in plot_baseline.GROUPS for m, lab in ms]
    t = tables(section(md, "#### Eval awareness, Task 1 baseline"))[0]
    rows = {r[0]: r for r in t[1]}
    vals = [[num(rows[m][k]) for m, _, _ in models] for k in range(1, len(t[0]))]
    grouped(t[0][1:], vals, 160, logos, out / "eval-baseline",
            "Agents, of 160 per model (Task 1 baseline, both conditions, all four agents).", models=models, top=100, bar=16, pitch=104, names=True)
    print("Wrote results/task1-boards, task2, task3, task4, task1-severity (each also -push), eval-baseline (.svg)")

if __name__ == "__main__":
    main()
