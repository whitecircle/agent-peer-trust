# Code for Help Peer: Good Teammates Can Be Fooled

Experiments on how agent swarms behave when agents differ in what they can do or are allowed to do.

## Requirements

- [uv](https://docs.astral.sh/uv/) and Python 3.11 or later. The scripts declare their own dependencies, so
  `uv run swarm.py ...` installs them.
- An [OpenRouter](https://openrouter.ai) API key in `OPENROUTER_API_KEY`. Every model call and every judge call
  goes through it, except agents on the Claude Code backend.
- Node.js 22.13 or later (the first with a stable `--permission` flag), for the package registry environment only
  (it runs each package's tests).
- For `backend = "claude-code"` configs only: [Claude Code](https://claude.com/claude-code), logged in to a Claude
  subscription, and `ANTHROPIC_API_KEY` unset.

Each config pins every model to one OpenRouter provider. Those are the providers the results were run on. A provider
may not be available to your key, or may have gone since: change `provider` in the config, or remove it to let
OpenRouter choose.

## Run it in a container

The package registry environment runs code that the models write: each agent edits a JavaScript package, and the
harness runs its tests with `node --permission`, allowed to read one temporary folder, for at most 10 seconds.
Node's permission model limits the damage but is not a sandbox. The other environments run no model-written code.
We ran everything directly on a laptop; don't copy that. Use a container or a throwaway VM:

```
docker build -t tool-asymmetries .
mkdir -p runs && chmod a+rwx runs   # the container's user writes the batches here
docker run --rm -it -e OPENROUTER_API_KEY -v "$PWD/runs:/work/runs" tool-asymmetries uv run swarm.py configs/pilot.toml
```

The model-written JavaScript runs with an empty environment apart from `PATH`, so it never sees `OPENROUTER_API_KEY`.

The Claude Code backend starts Claude Code with permission prompts off. It gives the model no built-in tools, only
the harness's own, loads no settings or project instructions, and runs in an empty folder. Claude Code still tells the
model a few things about the account it runs under: in one episode an agent's reasoning mentioned the domain of the
account's email address.

## The task

`swarm.py` runs **episodes**: N agents (default 4) share a message board, and each must fetch a
personal item from a mock portal and submit it. Targets either lack `fetch` (`cant`) or have it
but are told they may not use it (`not_allowed`); `baseline` gives everyone access. See the
docstring for details.

Agents take turns in a fixed order, one model call each per round. Each agent has its own token
budget, `tokens_per_agent` (all input, cached or not, plus output). It is enforced before every
call, retries included: each call's `max_tokens` is limited to what the agent has left after a high
estimate of the call's input, and an agent that can't afford another call gets no more turns. An
episode ends when every agent has submitted correctly or been dropped; when every agent still
unsolved has run out of budget; or after `idle_rounds` rounds (default 20) in which no agent used a
tool other than `read_board`, recorded as `stop = "idle"`. Older configs set `token_budget` for the
whole episode, which is split evenly between agents.
Usage and OpenRouter's billed cost are tracked per agent.

A config can list `[[variants]]`, each a named setting run against the same grid. Without any,
every episode uses `{name = "default"}`. The keys are independent, so one variant can combine any
of them (e.g. `delete` + `watched` + an injection). Keys:

- `action`: `read` (fetch then submit; the default), `edit` (set your record's status to "ready")
  or `delete` (delete your record). Same structure: holders can act on anyone's item.
- `watched`: the action tool's description says every call is logged and reviewed.
- `audit`: every action call posts a line to the board naming the caller and whose item it was.
- `confirm_others`: the first time an agent uses the action tool on another agent's item, the tool
  does nothing and asks "This is agent-N's …, not yours. Are you sure?"; the same call again goes ahead.
- `pull_board`: new board messages are no longer put into each turn; agents get a `read_board` tool
  and see only what they choose to read. Reads are logged per agent.
  `pull_board = "check"` also asks them, in the prompt, to check the board at the start of each turn.
- `injections`: messages on the board before round 1 that no agent wrote. `sender` is `holder` or
  `target` (the first agent with that role in turn order) or a literal name such as `operator`;
  `text` can use `{sender}`, `{item}`, `{url}` and `{tool}`. The named agent doesn't see the message
  unless `show_to_sender = true`, as with its own posts.
- `announce_past`: false leaves out the prompt's line that the board has messages from earlier agents
  (written histories and late joiners add it by default).
- `attacker_agent`: the first agent is the attacker's: `prompt` replaces its system prompt (`{id}`, `{n}`, `{roster}`,
  `{board}`), and `model` and `provider` can seat another model there; or `script`, a list of posts, one per
  round, replaces the model. Its role is logged as `attacker`.
- `same_user`: what agents are told about each other: `team` (they are a team working for one user), `told`
  (they all work for the same user) or `check` (the same, with a `user_of` tool that confirms it for any agent
  of the swarm).
- `note`: text put in every agent's first turn, after "Turn 1." and before the board, with no sender.

`seeds_by_condition` overrides `seeds` for particular conditions. `baseline` is a sanity check
(everyone has the tool and solves within two rounds), so configs run it with 5 seeds:
`seeds_by_condition = { baseline = 5 }`.

The seed sets the role layout (which turn positions are holders and which are targets) and the
item codes. Model sampling is not seeded.

If the API refuses a turn (its safety classifier), the attempt is discarded: the agent never sees
it and its tool calls do not run. The turn is attempted up to 5 times in total; if every attempt is refused,
the agent is dropped and takes no further turns. All attempts are logged.

## Running a batch

A config in `configs/` defines a grid of models × efforts × conditions × wordings × seeds. Each
model is pinned to one OpenRouter provider so every call goes to the same endpoint and
precision. One command runs it:

```
export OPENROUTER_API_KEY=...
uv run swarm.py configs/pilot.toml
```

A long batch needs the machine to stay awake (on a Mac, prefix the command with `caffeinate -is`). A batch that
stalls or dies can be resumed, as below.

Output goes to `runs/<config>-<timestamp>/` (git-ignored):

- `meta.json`: command, config, git commit, and any uncommitted files (diff in `uncommitted.patch`)
- `episodes/<model>-<effort>-<variant>-<condition>-<wording>-s<seed>/`
  - `events.jsonl`: everything, including each turn's exact input and the request IDs
  - `transcript.md`: the full episode in reading order
  - `summary.json`: harness counts
  - `descriptors/*.json`: descriptor outputs, added after the run
- `aggregate.md` and `agents.jsonl`: from `python3 aggregate.py runs/<batch>`; the second has one row
  per agent per episode (model, role, outcome, tokens, cost, requests, refusals, persistence, probing)

Every model call's billed cost is written to the episode's `events.jsonl` as it returns, so spend
survives interruptions. `python3 costs.py` totals it per batch and overall.

An episode in which an agent was dropped (every attempt at one of its turns refused or blocked by the provider) isn't
comparable with the others. `python3 rerun_dropped.py runs/<batch>` sets those episodes aside; resuming the batch runs
them again. `python3 plot_baseline.py` and `python3 plot_tables.py` draw the figures from a tables file (`results/tables.md`, not included).

If a batch is interrupted (an API failure, a closed laptop), resume it with
`uv run swarm.py runs/<batch>`. Finished episodes are kept; unfinished or
failed ones are moved aside as `<name>.attempt-<time>` and run again.

Commit before running so each batch maps to a clean commit.

## Helper scripts

- `scripts/run_boards.sh <config>`: run a batch and its judges, rerun episodes with a dropped agent until none is left, then judge eval awareness.
- `scripts/judge_only.sh <batch> ...`: the same judges on finished episodes, without resuming the batch.
- `scripts/make_pull.py`: write the `configs/pull-*.toml` configs (the main tables with the board as a `read_board` result) from the original settings.
- `scripts/to_cc.py <config> [variants]`: write a copy of a config on the Claude Code backend (`configs/<config>-ccx.toml`).
- `scripts/locate.py quotes.json`: find where quotes come from and print a footnote for each.

## Claude Code backend (subscription)

`backend = "claude-code"` in a config runs every agent through Claude Code on the logged-in Claude
subscription (`claude_code.py`, via the Agent SDK) instead of OpenRouter. It exists for experiments that need the subscription rather than the API. Models are given as usual
(`model = "anthropic/claude-opus-5.5"`); `provider` is ignored.

Why some models ran on it. Through the API, Anthropic's safety classifier refuses some turns in these environments
before the model answers (its categories here were `cyber` and `reasoning_extraction`). The harness retries a refused
turn and drops the agent after five refusals, and on some boards that happened to most agents, so those runs measured
the classifier and not the model. The subscription route didn't refuse.
So Opus 5.5, Sonnet 5.5 and Fable 5.2 ran through Claude Code wherever a result depends on those boards; each table
says which backend it used. The two routes mostly agree but not always: Opus 5.5 was a little less willing through
Claude Code on the swarm-history boards, and one Sonnet 5.5 board gave 76/80 through OpenRouter and 3/80 through
Claude Code.

- Same episode loop: one model call per agent per turn (`max_turns=1`); tool calls run through the
  harness as they are made, and results reach the model when its session resumes next turn.
- Claude Code's own system prompt, built-in tools, settings and CLAUDE.md are replaced or switched off.
  The model sees the agent's system prompt and the harness tools, named `mcp__harness__<tool>`.
- The per-agent budget is enforced as usual; each call's output is capped through
  `CLAUDE_CODE_MAX_OUTPUT_TOKENS`.
- Usage counts against the subscription's limits. `cost` is logged as 0 and Claude Code's own estimate as
  `cost_notional`. A deadlocked 4-agent Opus 5.5 episode is about 330k tokens.
- Run it without `ANTHROPIC_API_KEY` set (the backend refuses to run otherwise, since Claude Code would
  then bill the API): `uv run swarm.py configs/<config>.toml`. Judging still goes
  through OpenRouter.

## Queueing batches

`jobs.py` queues configs and runs them side by side, each followed by its judges (`run.sh`):

    python3 jobs.py add configs/a.toml configs/b.toml
    python3 jobs.py work --parallel 6
    python3 jobs.py status

Jobs added while the worker runs are picked up; it exits when the queue is empty. A job interrupted
with its worker is resumed from its batch folder when a worker next starts. Job state and logs are in
`runs/jobs/`.

## Descriptors

Descriptors are LLM judges that read full transcripts, not summaries. Each one looks for one
thing and is specified in `descriptors/<name>.md`, including its output schema. After each
batch:

1. Structured descriptors on every episode with Haiku, falling back to Sonnet:
   `uv run judge.py runs/<batch> --part structured --model anthropic/claude-haiku-5.5 --effort low --provider amazon-bedrock --fallback anthropic/claude-sonnet-5.5`
2. Open-ended reading on 5 episodes per cell with Sonnet:
   `uv run judge.py runs/<batch> --part open --model anthropic/claude-sonnet-5.5 --effort medium --provider amazon-bedrock --sample 5`
3. Run `aggregate.py` on the batch, and read the `characterisation` fields.

Judges answer through one `record_<descriptor>` tool per descriptor; each answer is checked against
the shape in the descriptor's spec (the schema is generated from its example object) and retried if
it doesn't match. Each judge writes `descriptors/<name>.json` into the episode folder and logs its calls in
`runs/<batch>/judging-<out>.jsonl`. Haiku was calibrated against Opus (high), which judged the first
multi-model batch: see `compare.py` and `recall.py`.

Descriptors: one spec per file in `descriptors/`. `run.sh` runs the ones that apply to a batch's environment; `eval_awareness` is run separately (`--part eval_awareness`).

## Run data

This repository is the code only. The run data (every finished episode: transcript, event log, summary, judge outputs)
and the results tables built from it are not published yet. `results.py`, `results_environments.py`,
`plot_baseline.py` and `plot_tables.py` read them, and 18 configs reuse earlier episodes as swarm history
(`past = ["runs/..."]`), so those need the run data in `runs/`. Your own batches land in `runs/`; add them to `BATCHES`
in the results scripts to tabulate them. `swarm.py` and `judge.py` regenerate the results tables only where a
`results/` folder exists.

## Known issues

Left as they are, so the code matches the runs it produced. None of them occurred in our runs, so the results aren't
affected:
- Package registry: a test counts as passing if its output says `PASS`, so an agent could fake a pass. None did: no
  JavaScript file an agent wrote prints `PASS` or calls `process.exit`.
- Dataset IDs, `private_urls` ablation: the ordinary URL format still returns an agent's ID. No agent used it.
- Malformed model output can crash a package registry or shared storage episode; crashed episodes are rerun, so that
  behaviour would be under-sampled. Every crash in those environments was an API error, none from model output.
- Claude Code backend: a retried turn may resume the same session, so the model may see an attempt that was meant to
  be discarded (not confirmed). No Claude Code turn was retried.

## License

Apache 2.0 (`LICENSE`).
