"""LLM client — OpenAI-compatible (Ollama, Groq, etc.)

On utilise response_format=json_object plutôt que tool_use :
- Plus compatible avec les petits modèles (llama3.2:3b, mistral, etc.)
- Plus rapide sur CPU (pas d'overhead de parsing d'outils)
- Le schéma JSON est défini dans le prompt système
"""
from __future__ import annotations

import json
import re

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


def _extract_json(text: str) -> dict:
    """Extrait un objet JSON depuis une réponse texte (gère les blocs markdown)."""
    text = text.strip()
    # Supprimer les blocs de code markdown ```json ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    # Trouver le premier { ... } dans la réponse
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


async def call_tool(
    *,
    model: str,
    system: str,
    user: str,
    tool: dict,
    max_tokens: int = 2048,
    trace_name: str | None = None,
) -> tuple[dict, int, int]:
    """
    Appelle le modèle en mode JSON structuré.
    Le schéma JSON est extrait de tool['input_schema'] et inclus dans le prompt.
    Compatible avec les petits modèles locaux qui ne gèrent pas bien tool_use.
    """
    client = get_client()

    # Inclure le schéma JSON dans le prompt système pour guider la réponse
    schema_str = json.dumps(tool.get("input_schema", {}), ensure_ascii=False, indent=2)
    enriched_system = (
        f"{system}\n\n"
        f"IMPORTANT : Réponds UNIQUEMENT avec un objet JSON valide respectant ce schéma :\n"
        f"{schema_str}\n"
        f"Ne mets aucun texte avant ou après le JSON. Pas de markdown, pas d'explication."
    )

    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": enriched_system},
            {"role": "user", "content": user},
        ],
    )

    tok_in = response.usage.prompt_tokens if response.usage else 0
    tok_out = response.usage.completion_tokens if response.usage else 0

    content = response.choices[0].message.content or "{}"
    try:
        result = _extract_json(content)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(
            f"Le modèle n'a pas retourné un JSON valide (modèle={model}, outil={tool['name']}): {exc}\n"
            f"Réponse brute : {content[:300]}"
        ) from exc

    logger.debug(
        "llm_call",
        model=model,
        name=trace_name or tool["name"],
        tokens_in=tok_in,
        tokens_out=tok_out,
    )
    return result, tok_in, tok_out
