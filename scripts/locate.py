"""python3 locate.py quotes.json: {key: [batch_glob, quote]} -> footnote lines in the findings file's format."""
import json, glob, sys, os
for key, (pattern, quote) in json.load(open(sys.argv[1])).items():
    hit = None
    for f in sorted(glob.glob(f"runs/{pattern}/episodes/*/events.jsonl")):
        if ".attempt-" in f: continue
        for l in open(f):
            e = json.loads(l)
            if e["kind"] != "response": continue
            texts = [b.get("text") or b.get("thinking") or "" for b in e["content"]] + [json.dumps(b.get("input", {}), ensure_ascii=False) for b in e["content"] if b.get("type") == "tool_use"]
            if any(quote in t for t in texts):
                hit = (f, e["round"], e["agent"]); break
        if hit: break
    if not hit:
        print(f"[^{key}]: NOT FOUND {quote[:50]}"); continue
    f, rnd, agent = hit; ep = os.path.dirname(f); run, name = ep.split("/")[1], os.path.basename(ep)
    q = sorted(os.path.basename(d)[:-5] for d in glob.glob(ep + "/descriptors/*.json") if quote[:60] in open(d).read())
    tail = f" (quoted in {', '.join(x + '.json' for x in q)})" if q else ""
    print(f"[^{key}]: `{run}`, episode `{name}`, round {rnd}, {agent}. Judge outputs: `{ep}/descriptors/`{tail}.")
