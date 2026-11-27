"""Agreement between two judges' descriptor outputs on the same episodes.

  python3 compare.py runs/<batch> descriptors descriptors-haiku [descriptors-sonnet ...]

The first output folder is the reference. For each count, prints how often the candidate matches
exactly, the mean absolute difference, and both means; for persistence, how often the candidate
gives the same `ended` value for an agent.
"""

import json
import sys
from pathlib import Path


def load(d, name):
    f = d / f"{name}.json"
    return json.loads(f.read_text()) if f.exists() else None


def counts(d):
    api, sr, inter, probe = (load(d, n) for n in ["api_refusals", "self_refusals", "interactions", "edge_probing"])
    if None in (api, sr, inter, probe):
        return None
    responses = [r.get("response") for r in inter.get("responses", [])]
    return {
        "api refusals": len(api.get("refusals", [])),
        "self-refusals": sum(1 + (r.get("repeats") or 0) for r in sr.get("self_refusals", [])),
        "requests": len(inter.get("requests", [])),
        "responses complied": responses.count("complied"),
        "responses refused": responses.count("refused"),
        "responses ignored": responses.count("ignored"),
        "operator appeals": sum(1 + (r.get("repeats") or 0) for r in inter.get("operator_appeals", [])),
        "edge probes": len(probe.get("instances", [])),
    }, {p.get("agent"): p.get("ended") for p in inter.get("persistence", [])}


def main(batch, ref, *cands):
    eps = [e for e in sorted((Path(batch) / "episodes").iterdir()) if (e / ref).is_dir()]
    for cand in cands:
        pairs = [(counts(e / ref), counts(e / cand)) for e in eps if (e / cand).is_dir()]
        pairs = [(a, b) for a, b in pairs if a and b]
        print(f"\n{cand} vs {ref}: {len(pairs)} episodes")
        print(f"{'metric':22} {'exact':>6} {'mean |diff|':>12} {'ref mean':>9} {'cand mean':>10}")
        for k in pairs[0][0][0] if pairs else []:
            a = [p[0][0][k] for p in pairs]; b = [p[1][0][k] for p in pairs]
            exact = sum(x == y for x, y in zip(a, b)) / len(a)
            mad = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
            print(f"{k:22} {exact:6.0%} {mad:12.1f} {sum(a)/len(a):9.1f} {sum(b)/len(b):10.1f}")
        agents = [(p[0][1].get(ag), p[1][1].get(ag)) for p in pairs for ag in p[0][1]]
        if agents:
            print(f"{'persistence ended':22} {sum(x == y for x, y in agents) / len(agents):6.0%}   ({len(agents)} agent entries)")


if __name__ == "__main__":
    main(*sys.argv[1:])
