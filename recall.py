"""Recall of an open-ended judge on findings we already know about.

  python3 recall.py runs/<batch> descriptors-sonnet [descriptors-haiku ...]

For each entry in calibration/known-findings.json, checks whether the judge's anomalies.json for
that episode mentions any of the finding's keywords (case-insensitive) anywhere in its output.
Keyword matching is a coarse proxy: read the misses.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def main(batch, *outs):
    findings = json.loads((ROOT / "calibration" / "known-findings.json").read_text())
    for out in outs:
        hits = 0
        print(f"\n{out}")
        for f in findings:
            path = Path(batch) / "episodes" / f["episode"] / out / "anomalies.json"
            text = path.read_text().lower() if path.exists() else None
            hit = text is not None and any(k.lower() in text for k in f["keywords"])
            hits += hit
            print(f"  {'missing' if text is None else 'HIT ' if hit else 'miss'}  {f['episode']}: {f['finding']}")
        print(f"  recall {hits}/{len(findings)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
