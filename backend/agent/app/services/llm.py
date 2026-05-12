from __future__ import annotations

import structlog
from anthropic import AsyncAnthropic

from app.config import settings

logger = structlog.get_logger()

_anthropic: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic


async def call_tool(
    *,
    model: str,
    system: str,
    user: str,
    tool: dict,
    max_tokens: int = 4096,
    trace_name: str | None = None,
) -> tuple[dict, int, int]:
    """Call Claude with a single tool and return (tool_input, input_tokens, output_tokens)."""
    client = get_client()

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user}],
    )

    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens

    tool_block = next(b for b in response.content if b.type == "tool_use")
    logger.debug(
        "llm_call",
        model=model,
        name=trace_name or tool["name"],
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    return tool_block.input, tokens_in, tokens_out
