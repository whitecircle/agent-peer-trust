#!/bin/sh
# Run a batch (a config, or a batch folder to resume), then judge it; judge.py updates results/.
# Batches are independent, so run several at once (jobs.py queues them).
# The body is one function called on the last line, so the shell has read the whole file before it
# starts: editing this file while a batch runs can't change what that run does next.
main() {
  set -eu
  cd "$(dirname "$0")"
  batch=$(uv run -q swarm.py "$1" | tee /dev/stderr | sed -n 's/^Batch: //p' | tail -1)
  judge() { uv run -q judge.py "$batch" --provider amazon-bedrock "$@"; }
  environment=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1] + "/meta.json"))["config"].get("environment", "ids"))' "$batch")
  if [ "$environment" = ids ]; then
    judge --part structured --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
    judge --part open --model anthropic/claude-sonnet-5.5 --effort medium --sample 5
    judge --part own_tool_use --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
    judge --part harm --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
    judge --part safety_lead --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
  else
    judge --part injection --model anthropic/claude-haiku-5.5 --effort low --fallback anthropic/claude-sonnet-5.5
    judge --part injection_open --model anthropic/claude-sonnet-5.5 --effort medium --sample 5
  fi
  uv run -q aggregate.py "$batch" > /dev/null
  echo "Done: $batch"
}
main "$@"; exit
