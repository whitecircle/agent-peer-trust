#!/bin/sh
# usage: judge_only.sh <batch> ...  (with OPENROUTER_API_KEY set): run.sh's judges and eval awareness on finished
# episodes only, without resuming the batch (for batches whose own key can't be used any more)
for batch in "$@"; do
  judge() { uv run -q judge.py "$batch" --provider amazon-bedrock "$@" 2>&1 | grep -v ": ok" | tail -2; }
  environment=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1] + "/meta.json"))["config"].get("environment", "ids"))' "$batch")
  if [ "$environment" = ids ]; then
    judge --part structured --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
    judge --part open --model anthropic/claude-sonnet-5.5 --effort medium --sample 5
    judge --part own_tool_use --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
  else
    judge --part injection --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
    judge --part injection_open --model anthropic/claude-sonnet-5.5 --effort medium --sample 5
  fi
  judge --part eval_awareness --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
  uv run -q aggregate.py "$batch" > /dev/null
  echo "judged: $batch"
done
