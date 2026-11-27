#!/bin/sh
# usage: run_boards.sh <config>  (with OPENROUTER_API_KEY set): batch + judges, rerun dropped until clean, eval awareness
cfg=$1
batch=$(sh run.sh "$cfg" | sed -n 's/^Done: //p' | tail -1)
echo "batch $batch"
i=0; while [ $i -lt 30 ]; do i=$((i+1))
  [ "$(python3 rerun_dropped.py "$batch" --dry-run | tail -1 | cut -d' ' -f1)" = 0 ] && { echo "clean after $((i-1)) reruns"; break; }
  python3 rerun_dropped.py "$batch" | tail -1
  sh run.sh "$batch" | grep -E "FAILED|Done" | cut -c1-160
done
uv run -q judge.py "$batch" --part eval_awareness --model anthropic/claude-haiku-5.5 --effort low --provider amazon-bedrock --fallback anthropic/claude-sonnet-5.5 2>&1 | grep -v ": ok" | tail -2
echo finished
