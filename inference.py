"""Model calls through OpenRouter's Anthropic-compatible endpoint, shared by swarm.py and judge.py.

OpenRouter passes rate limits (429) and overload (529) back to the caller; it only falls back
between providers when allowed, and we pin one provider per model. The Anthropic SDK retries a few
times with backoff capped at 8 seconds, which doesn't outlast a busy provider, so `patient` waits
longer on top of it.
"""

import os
import time

import anthropic
import httpx


def client():
    return anthropic.Anthropic(base_url="https://openrouter.ai/api", auth_token=os.environ["OPENROUTER_API_KEY"],
                               api_key=None, max_retries=5)


def pinned(provider):
    """Request extra_body that sends every call to one provider, with no fallback."""
    return {"provider": {"order": [provider], "allow_fallbacks": False}} if provider else None


def patient(call, note=lambda wait: None, waits=(30, 60, 120, 240, 480, 600, 600)):
    """Make a call, waiting out rate limits and overload for up to about 35 minutes beyond the SDK's
    own retries. note(wait) is called before each wait, for logging."""
    for wait in waits:
        try:
            return call()
        except anthropic.APIStatusError as e:
            if e.status_code not in (429, 529):
                raise
            note(wait)
            time.sleep(wait)
    return call()


def prices(model):
    """Per-token prices from OpenRouter's model list, for estimating a call's cost when the response
    doesn't carry it (streamed responses)."""
    m = next(m for m in httpx.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"] if m["id"] == model)
    p = m["pricing"]
    return {k: float(p.get(k) or 0) for k in ["prompt", "completion", "input_cache_read", "input_cache_write"]}
