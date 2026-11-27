"""Agents served by Claude Code on the user's Claude subscription, through the Agent SDK.

For experiments that need the subscription rather than the API. The episode loop is unchanged: one
model call per agent per turn (max_turns=1). The agent's tool calls run through the harness as they are
made, and their results reach the model at the start of its next turn, when its session resumes; the
same order as the API backend. Claude Code's own system prompt, built-in tools, settings and CLAUDE.md
are all replaced or switched off, so the model sees the agent's system prompt and the harness tools only
(named mcp__harness__<tool> rather than <tool>).

Usage counts against the subscription's limits, not an API bill; the cost Claude Code reports is logged
as `cost_notional`, and `cost` is 0 so that `costs.py` totals real spend only.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, RateLimitEvent, ResultError, ResultMessage,
                              TextBlock, ThinkingBlock, ToolUseBlock, create_sdk_mcp_server, query, tool)

SERVER = "harness"
EMPTY = tempfile.mkdtemp(prefix="claude-code-agent-")  # working directory with no CLAUDE.md, settings or files
WAITS = (30, 60, 120, 240, 480, 600, 600)  # rate limits and overload, as inference.patient
LIMITS = Path(__file__).parent / "runs" / "claude-code-limits.jsonl"  # the plan's limit status, as Claude Code reports it


def model_id(model):
    """anthropic/claude-opus-5.5 -> claude-opus-5-5"""
    return model.split("/")[-1].replace(".", "-")


def turn(agent, text, max_tokens, effort, run_tool, note=lambda wait: None):
    """One model call for `agent`, resuming its Claude Code session (agent.session). Each tool call goes
    through run_tool(name, input) -> result text as the model makes it. Returns the response's content
    blocks (as dicts, tool names without the MCP prefix), usage, stop reason, notional cost and session id."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is set: Claude Code would bill the API instead of the subscription")
    for wait in WAITS + (None,):
        out = asyncio.run(_turn(agent, text, max_tokens, effort, run_tool))
        if out["api_error_status"] not in (429, 529) or wait is None:
            return out
        note(wait)
        time.sleep(wait)


def block(b):
    if isinstance(b, ThinkingBlock):
        return {"type": "thinking", "thinking": b.thinking}
    if isinstance(b, TextBlock):
        return {"type": "text", "text": b.text}
    if isinstance(b, ToolUseBlock):
        return {"type": "tool_use", "id": b.id, "name": b.name.removeprefix(f"mcp__{SERVER}__"), "input": b.input}
    return {"type": type(b).__name__}


async def _turn(agent, text, max_tokens, effort, run_tool):
    def handler(name):
        async def call(args):
            result = run_tool(name, args)
            return {"content": [{"type": "text", "text": result}], **({"is_error": True} if result.startswith("Error:") else {})}
        return call

    server = create_sdk_mcp_server(name=SERVER, version="1.0.0", tools=[
        tool(t["name"], t["description"], t["input_schema"])(handler(t["name"])) for t in agent.tools])
    options = ClaudeAgentOptions(
        system_prompt=agent.system, model=model_id(agent.model), effort=effort,
        thinking={"type": "adaptive", "display": "summarized"},
        tools=[], mcp_servers={SERVER: server}, strict_mcp_config=True,
        allowed_tools=[f"mcp__{SERVER}__{t['name']}" for t in agent.tools], permission_mode="bypassPermissions",
        max_turns=1, setting_sources=[], cwd=EMPTY, resume=agent.session,
        env={"CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(max_tokens)})
    content, data = [], {}
    try:
        async for m in query(prompt=text, options=options):
            if isinstance(m, AssistantMessage):
                content += [block(b) for b in m.content]
            elif isinstance(m, RateLimitEvent):
                with LIMITS.open("a") as f:
                    f.write(json.dumps({"t": time.time(), **m.rate_limit_info.raw}) + "\n")
            elif isinstance(m, ResultMessage):
                data = {"usage": m.usage, "total_cost_usd": m.total_cost_usd, "session_id": m.session_id,
                        "stop_reason": getattr(m, "stop_reason", None)}
    except ResultError as e:  # max_turns=1 ends every turn that makes a tool call this way
        data = e.data or {}
    return {"content": content, "usage": data.get("usage") or {}, "stop_reason": data.get("stop_reason"),
            "cost_notional": data.get("total_cost_usd") or 0, "session_id": data.get("session_id"),
            "api_error_status": data.get("api_error_status")}
