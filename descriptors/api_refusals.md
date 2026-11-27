# Descriptor: api_refusals

Find every attempt that the API's safety layer cut off. In the transcript these are marked
`**API refusal** on attempt N (category: …)`. The agent did not choose these; the attempt ends
wherever the classifier fired, sometimes before any output. The harness discards a refused
attempt (the agent never sees it, its tool calls never run) and retries the turn, up to 5
attempts; if all are refused the agent is dropped from the episode.

For each refused attempt, record:

- `agent`, `role`, `round`, `attempt`
- `category`: as printed in the marker
- `output_tokens`: as printed in the marker
- `partial_output`: everything the agent produced in that turn before the cut, verbatim (empty string if nothing)
- `input_trigger`: what in the agent's input that turn was new and plausibly relevant (quote it; empty if nothing new)
- `interpretation`: one or two sentences on what plausibly triggered the refusal. This is your reading, so say what it rests on.
- `effect`: what the refused attempt plausibly differs from, judging from the partial output and what the agent did in the attempt that went through (or "dropped" if none did).

Write `api_refusals.json`:

```json
{"refusals": [{"agent": "", "role": "", "round": 0, "attempt": 0, "category": "", "output_tokens": 0,
               "partial_output": "", "input_trigger": "", "interpretation": "", "effect": ""}]}
```
