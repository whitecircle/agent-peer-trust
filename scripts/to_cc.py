"""Write configs/<src>-ccx.toml: the source config on the Claude Code backend, Anthropic models only (Kimi in mixed swarms
moves to deepinfra/bf16), variant names marked -claude-code, at most 10 workers. Optional: only the named variants."""
import re, sys, tomllib
src, keep = sys.argv[1], set(sys.argv[2:])
text = open(f"configs/{src}.toml").read()
parts = re.split(r"(?m)^(?=\[\[(?:models|variants|mix)\]\])", text)
head, blocks = parts[0], parts[1:]
out_blocks = []
for b in blocks:
    kind = re.match(r"\[\[(\w+)\]\]", b)[1]
    if kind == "models":
        m = re.search(r'model = "([^"]+)"', b)[1]
        if not m.startswith("anthropic/"):
            continue
        b = re.sub(r'(?m)^provider = .*\n', "", b)
    elif kind == "mix":
        if 'model = "anthropic/' in b:
            b = re.sub(r'(?m)^provider = .*\n', "", b)
        else:
            b = re.sub(r'(?m)^provider = .*$', 'provider = "deepinfra/bf16"', b)
    else:
        name = re.search(r'name = "([^"]+)"', b)[1]
        if keep and name not in keep:
            continue
        b = b.replace(f'name = "{name}"', f'name = "{name}-claude-code"', 1)
    out_blocks.append(b)
head = re.sub(r'(?m)^workers = \d+', "workers = 10", head)
head = re.sub(r'(?m)^backend = .*\n', "", head)
lines = head.split("\n")
i = next(i for i, l in enumerate(lines) if l and not l.startswith("#"))
lines.insert(i, 'backend = "claude-code"')
if 'mix_name' in head:
    lines = [re.sub(r'mix_name = "([^"]+)"', r'mix_name = "\1-ccx"', l) for l in lines]
doc = f"# Claude Code rerun of {src}.toml (Anthropic models only), so every Anthropic number comes from one backend.\n"
out = doc + "\n".join(lines) + "".join(out_blocks)
cfg = tomllib.loads(out)
assert cfg.get("models") or cfg.get("mix"), src
open(f"configs/{src}-ccx.toml", "w").write(out)
print(src, [m.get("model") for m in cfg.get("models", [])] or [m["model"] for m in cfg["mix"]], [v["name"] for v in cfg.get("variants", [{"name": "default"}])][:6])
