"""API spend per batch and in total, read from the event logs.

Every model call's billed cost is written to its episode's events.jsonl as the call returns, so
these totals include unfinished and interrupted episodes. Judge calls made with judge.py are
logged per batch in judging*.jsonl and counted too. Judges run in Claude Code, not through
OpenRouter; their token counts are kept by hand in runs/ledger.jsonl.

  python3 costs.py
"""

import json
from pathlib import Path

RUNS = Path(__file__).parent / "runs"
TOKEN_KEYS = ["input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"]


def batches():
    return sorted(d for d in RUNS.iterdir() if d.is_dir() and any(d.rglob("events.jsonl")))


def spend(batch):
    total = {"cost": 0.0, "tokens": 0, "calls": 0, "episodes": 0}
    for f in list(Path(batch).rglob("events.jsonl")) + list(Path(batch).glob("judging*.jsonl")):
        total["episodes"] += f.name == "events.jsonl"
        for line in f.open():
            e = json.loads(line)
            if e["kind"] in ("response", "judge"):
                u = e["usage"] or {}
                total["cost"] += u.get("cost") or 0
                total["tokens"] += sum(u.get(k) or 0 for k in TOKEN_KEYS)
                total["calls"] += 1
    return total


def main():
    rows = [(d.name, spend(d)) for d in batches()]
    for name, s in rows:
        print(f"{name:45} {s['episodes']:4} episodes {s['calls']:6} calls {s['tokens']:>13,} tokens  ${s['cost']:8.2f}")
    print(f"{'total API spend':45} {'':39} ${sum(s['cost'] for _, s in rows):8.2f}")
    ledger = RUNS / "ledger.jsonl"
    judges = [json.loads(l) for l in ledger.open() if json.loads(l).get("kind") == "judges"] if ledger.exists() else []
    print(f"judge tokens (Claude Code, not billed through OpenRouter): {sum(j['tokens'] or 0 for j in judges):,} over {len(judges)} judge runs")


if __name__ == "__main__":
    main()
