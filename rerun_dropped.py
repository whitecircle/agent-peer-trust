"""Set aside the episodes of a batch in which an agent was dropped (every attempt at one of its turns refused or
blocked), so that resuming the batch runs them again. An episode with a dropped agent isn't comparable with the
others: the swarm lost a member. Each is renamed <name>.attempt-<time>-dropped, as swarm.py does with failed ones.

  python3 rerun_dropped.py runs/<batch> [--match <text in the episode name>] [--dry-run]

Prints how many it set aside; then resume the batch (uv run swarm.py runs/<batch>) and repeat until none are left.
`attempts` counts, per episode, the runs set aside before the one kept.
"""

import argparse
import json
import time
from pathlib import Path


def dropped(batch, match=""):
    return [e for e in sorted((batch / "episodes").iterdir())
            if ".attempt-" not in e.name and match in e.name and (e / "summary.json").exists()
            and json.loads((e / "summary.json").read_text())["dropped"]]


def attempts(batch):
    """Episode name -> how many runs of it were set aside because an agent was dropped."""
    out = {}
    for e in (batch / "episodes").iterdir():
        if e.name.endswith("-dropped"):
            name = e.name.split(".attempt-")[0]
            out[name] = out.get(name, 0) + 1
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("batch", type=Path)
    p.add_argument("--match", default="")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    eps = dropped(args.batch, args.match)
    now = time.strftime("%Y%m%d-%H%M%S")
    for e in eps:
        print(e.name, json.loads((e / "summary.json").read_text())["dropped"])
        if not args.dry_run:
            e.rename(e.with_name(f"{e.name}.attempt-{now}-dropped"))
    print(f"{len(eps)} episodes with a dropped agent" + (" (dry run)" if args.dry_run else ", set aside"))


if __name__ == "__main__":
    main()
