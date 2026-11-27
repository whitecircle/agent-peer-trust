"""Tabulate a batch: harness counts from summary.json, descriptor counts from descriptors/*.json.

Writes aggregate.md (one row per cell) and agents.jsonl (one row per agent per episode, so
behaviour can be traced to individual agents and, in mixed swarms, to their models).

  python3 aggregate.py runs/<batch>
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def main(batch):
    batch = Path(batch)
    groups = defaultdict(list)
    for ep in sorted((batch / "episodes").iterdir()):
        if ".attempt-" in ep.name:  # set aside when the batch was resumed; rerun under the plain name
            continue
        s = load(ep / "summary.json")
        if s is None:
            groups["failed"].append(ep.name)
            continue
        groups[(s.get("model", "anthropic/claude-opus-5.5"), s.get("effort", "medium"), s.get("variant", {}).get("name", "default"), s["condition"], s["wording"])].append((s, ep / "descriptors"))
    failed = groups.pop("failed", [])

    rows = []
    for (model, effort, variant, condition, wording), eps in groups.items():
        targets = [a for s, _ in eps for a, r in s["roles"].items() if r == "target"]
        solved = lambda role: sum(s["solved"][a] for s, _ in eps for a, r in s["roles"].items() if r == role)
        holders = [a for s, _ in eps for a, r in s["roles"].items() if r == "holder"]
        d = lambda name: [load(dd / f"{name}.json") for _, dd in eps]
        inter = [x for x in d("interactions") if x]
        self_ref = [x for x in d("self_refusals") if x]
        responses = Counter(r["response"] for x in inter for r in x["responses"])
        rows.append({
            "model": model.split("/")[-1],
            "effort": effort,
            "variant": variant,
            "condition": condition,
            "wording": wording,
            "episodes": len(eps),
            "targets solved": f"{solved('target')}/{len(targets)}",
            "holders solved": f"{solved('holder')}/{len(holders)}",
            "eps with API refusal": sum(bool(s["refusals"]) for s, _ in eps),
            "API refusals": sum(len(s["refusals"]) for s, _ in eps),
            "dropped agents": sum(len(s.get("dropped", [])) for s, _ in eps),
            # summaries before the action-severity ablation call these target_self_fetches / proxy_fetches
            "eps with target self-action": sum(bool(s.get("target_self_actions", s.get("target_self_fetches"))) for s, _ in eps),
            "eps with proxy action": sum(bool(s.get("proxy_actions", s.get("proxy_fetches"))) for s, _ in eps),
            "described": len(inter),
            "self-refusals": sum(1 + r.get("repeats", 0) for x in self_ref for r in x["self_refusals"]),
            "target requests": sum(len(x["requests"]) for x in inter),
            "holder responses": ", ".join(f"{k} {v}" for k, v in sorted(responses.items())) or "-",
            "operator appeals": sum(1 + r.get("repeats", 0) for x in inter for r in x.get("operator_appeals", [])),
            "probes": sum(len(x.get("probes", [])) for x in inter),
            "edge probes": sum(len(x["instances"]) for x in d("edge_probing") if x),
            "median rounds": sorted(s.get("rounds", 0) for s, _ in eps)[len(eps) // 2],
            # batches before per-episode cost tracking have no cost in their summaries
            "cost": f"${sum(s['usage']['cost'] for s, _ in eps):.2f}" if all("cost" in s["usage"] for s, _ in eps) else "-",
        })

    cols = list(rows[0]) if rows else []
    table = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    table += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    if failed:
        table += ["", "Failed episodes: " + ", ".join(failed)]
    out = "\n".join(table)
    (batch / "aggregate.md").write_text(out + "\n")
    print(out)

    with (batch / "agents.jsonl").open("w") as f:
        for eps in groups.values():
            for s, dd in eps:
                for row in agent_rows(s, dd):
                    f.write(json.dumps(row) + "\n")


def agent_rows(s, dd):
    inter = load(dd / "interactions.json") or {}
    self_ref = (load(dd / "self_refusals.json") or {}).get("self_refusals", [])
    probes = (load(dd / "edge_probing.json") or {}).get("instances", [])
    persistence = {x["agent"]: x for x in inter.get("persistence", [])}
    usage = s.get("usage_by_agent", {})
    for position, (agent, role) in enumerate(s["roles"].items(), 1):
        p = persistence.get(agent, {})
        yield {
            "episode": f"{s['condition']}-{s['wording']}-s{s['seed']}",
            "model": s.get("models", {}).get(agent, s.get("model")),  # per-agent model in mixed swarms
            "effort": s.get("effort"), "variant": s.get("variant", {}).get("name", "default"),
            "condition": s["condition"], "wording": s["wording"], "seed": s["seed"],
            "agent": agent, "role": role, "turn_position": position,
            "solved": s["solved"][agent], "dropped": agent in s.get("dropped", []),
            "tokens": sum(usage.get(agent, {}).get(k, 0) for k in
                          ["input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"]),
            "cost": usage.get(agent, {}).get("cost"),
            "api_refusals": sum(r["agent"] == agent for r in s["refusals"]),
            "requests_made": sum(r["agent"] == agent for r in inter.get("requests", [])),
            "request_rounds": [r["round"] for r in inter.get("requests", []) if r["agent"] == agent],
            "responses": Counter(r["response"] for r in inter.get("responses", []) if r["holder"] == agent),
            "self_refusals": sum(1 + r.get("repeats", 0) for r in self_ref if r["agent"] == agent),
            "operator_appeals": sum(1 + r.get("repeats", 0) for r in inter.get("operator_appeals", []) if r["agent"] == agent),
            "edge_probes": sum(r["agent"] == agent for r in probes),
            "persistence": {k: p.get(k) for k in ["aim", "first_round", "last_round", "turns_pursuing", "ended", "ended_round"]} if p else None,
            "tactics": [t["tactic"] for t in p.get("tactics", [])],
            "board_reads": sum(r["agent"] == agent for r in s.get("board_reads", [])),
        }


if __name__ == "__main__":
    main(sys.argv[1])
