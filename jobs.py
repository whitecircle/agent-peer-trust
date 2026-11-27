"""Job queue for batches: queue configs, and a worker runs them side by side, each followed by its
judges (run.sh).

  python3 jobs.py add configs/a.toml [configs/b.toml ...]
  python3 jobs.py status
  OPENROUTER_API_KEY=... python3 jobs.py work [--parallel 6]

A job is runs/jobs/<n>.json (config, state, batch folder) with its log in runs/jobs/<n>.log. States:
queued, running, done, failed. The worker runs up to --parallel jobs at once and checks the queue
every 30 seconds, so jobs added while it runs are picked up; it exits when nothing is queued or
running. A job still marked running when a worker starts was interrupted, and is resumed from its
batch folder: finished episodes are kept and finished judging is skipped.
"""

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import costs

ROOT = Path(__file__).parent
JOBS = ROOT / "runs" / "jobs"


def jobs():
    return [json.loads(f.read_text()) for f in sorted(JOBS.glob("*.json"), key=lambda f: int(f.stem))]


def save(job):
    (JOBS / f"{job['id']}.json").write_text(json.dumps(job, indent=1))


def batch_of(job):
    """The batch folder from the job's log: swarm.py prints it first thing."""
    log = JOBS / f"{job['id']}.log"
    found = re.findall(r"^Batch: (.+)$", log.read_text(), re.M) if log.exists() else []
    return found[-1] if found else None


def add(configs):
    JOBS.mkdir(parents=True, exist_ok=True)
    n = max([j["id"] for j in jobs()], default=0)
    for i, config in enumerate(configs, n + 1):
        if not Path(config).exists():
            raise SystemExit(f"no such config: {config}")
        save({"id": i, "config": config, "state": "queued", "added": time.strftime("%Y-%m-%dT%H:%M:%S")})
        print(f"job {i}: {config} queued")


def status():
    for j in jobs():
        batch = batch_of(j)
        done = len(list(Path(batch).glob("episodes/*/summary.json"))) if batch else 0
        cost = costs.spend(batch)["cost"] if batch else 0
        print(f"{j['id']:>3}  {j['state']:8} {j['config']:45} {done:>4} episodes  ${cost:7.2f}  {Path(batch).name if batch else ''}")


def work(parallel):
    running = {}
    for j in jobs():
        if j["state"] == "running":  # interrupted by an earlier worker
            j["state"] = "queued"
            save(j)
    while True:
        for id, proc in list(running.items()):
            if proc.poll() is not None:
                j = json.loads((JOBS / f"{id}.json").read_text())
                j["state"] = "done" if proc.returncode == 0 else "failed"
                j["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                save(j)
                print(f"job {id}: {j['state']} ({j['config']})", flush=True)
                del running[id]
        queued = [j for j in jobs() if j["state"] == "queued"]
        for j in queued[:max(0, parallel - len(running))]:
            target = batch_of(j) or j["config"]  # resume the batch if it was started
            log = (JOBS / f"{j['id']}.log").open("a")
            running[j["id"]] = subprocess.Popen(["sh", str(ROOT / "run.sh"), target], stdout=log, stderr=subprocess.STDOUT)
            j["state"] = "running"
            j.setdefault("started", time.strftime("%Y-%m-%dT%H:%M:%S"))
            save(j)
            print(f"job {j['id']}: running {target}", flush=True)
        if not running and not queued:
            return
        time.sleep(30)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("add").add_argument("configs", nargs="+")
    sub.add_parser("status")
    sub.add_parser("work").add_argument("--parallel", type=int, default=6)
    args = p.parse_args()
    {"add": lambda: add(args.configs), "status": status, "work": lambda: work(args.parallel)}[args.cmd]()
