"""LLM client — OpenAI-compatible (Ollama, Groq, Together AI, etc.)

Les prompts définissent les outils au format Anthropic (input_schema).
Ce module les convertit automatiquement en format OpenAI (parameters)
avant l'appel, et renvoie toujours (result_dict, tokens_in, tokens_out).
"""
from __future__ import annotations

import json

import structlog
from openai import AsyncOpenAI

from app.config import settings

logger = structlog.get_logger()

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    return _client


def _to_openai_tool(anthropic_tool: dict) -> dict:
    """Convertit le format Anthropic → format OpenAI function-calling."""
    return {
        "type": "function",
        "function": {
            "name": anthropic_tool["name"],
            "description": anthropic_tool.get("description", ""),
            "parameters": anthropic_tool["input_schema"],
        },
    }


async def call_tool(
    *,
    model: str,
    system: str,
    user: str,
    tool: dict,
    max_tokens: int = 4096,
    trace_name: str | None = None,
) -> tuple[dict, int, int]:
    """Appelle le modèle avec un outil et retourne (résultat, tokens_in, tokens_out)."""
    client = get_client()
    oai_tool = _to_openai_tool(tool)

    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        tools=[oai_tool],
        tool_choice={"type": "function", "function": {"name": tool["name"]}},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    tok_in = response.usage.prompt_tokens if response.usage else 0
    tok_out = response.usage.completion_tokens if response.usage else 0

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError(f"Le modèle n'a pas retourné d'appel d'outil (nom={tool['name']})")

    result = json.loads(tool_calls[0].function.arguments)

    logger.debug(
        "llm_call",
        model=model,
        name=trace_name or tool["name"],
        tokens_in=tok_in,
        tokens_out=tok_out,
    )
    return result, tok_in, tok_out
