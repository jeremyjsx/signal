import json
import re
from typing import Any

from groq import AsyncGroq

from app.core.config import settings

AI_MODEL_NAME = "llama-3.1-8b-instant"


def _clamp_score(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def _normalize_decision(value: Any, final_score: float) -> str:
    decision = str(value or "").strip().lower()
    if decision in {"keep", "discard"}:
        return decision
    return "keep" if final_score >= settings.ai_relevance_threshold else "discard"


def _default_analysis() -> dict:
    return {
        "relevance_score": 0.0,
        "backend_depth_score": 0.0,
        "novelty_score": 0.0,
        "actionability_score": 0.0,
        "linkedin_potential_score": 0.0,
        "final_score": 0.0,
        "decision": "discard",
        "reasoning_summary": "LLM scoring fallback",
        "model_name": AI_MODEL_NAME,
    }


def _normalize_analysis_item(item: Any) -> dict:
    default = _default_analysis()
    if not isinstance(item, dict):
        return default

    relevance = _clamp_score(item.get("relevance_score"))
    backend_depth = _clamp_score(item.get("backend_depth_score"))
    novelty = _clamp_score(item.get("novelty_score"))
    actionability = _clamp_score(item.get("actionability_score"))
    linkedin_potential = _clamp_score(item.get("linkedin_potential_score"))
    weighted = (
        (0.4 * relevance)
        + (0.25 * backend_depth)
        + (0.15 * novelty)
        + (0.1 * actionability)
        + (0.1 * linkedin_potential)
    )
    final_score = _clamp_score(item.get("final_score", weighted))
    reasoning = str(item.get("reasoning_summary") or "").strip() or "No reasoning provided."
    decision = _normalize_decision(item.get("decision"), final_score)
    return {
        "relevance_score": relevance,
        "backend_depth_score": backend_depth,
        "novelty_score": novelty,
        "actionability_score": actionability,
        "linkedin_potential_score": linkedin_potential,
        "final_score": final_score,
        "decision": decision,
        "reasoning_summary": reasoning[:1000],
        "model_name": AI_MODEL_NAME,
    }


def _parse_json_array(content: str) -> list[dict]:
    cleaned = content.strip()
    fence_match = re.search(r"```(?:json)?\s*(\[.*\])\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        return []
    return [_normalize_analysis_item(item) for item in data]


async def analyze_articles_batch(articles: list) -> list[dict]:
    """Analyze articles and return structured scoring metadata."""
    if not settings.groq_api_key:
        return [_default_analysis() for _ in articles]

    if not articles:
        return []

    client = AsyncGroq(api_key=settings.groq_api_key)

    articles_text = "\n".join(
        [
            f"{i + 1}. title={title[:120]!r}, summary={summary[:220] if summary else ''!r}"
            for i, (title, summary) in enumerate(articles)
        ]
    )

    prompt = f"""You are scoring engineering articles for a backend engineer.
Return STRICT JSON only: an array with exactly {len(articles)} objects.
No markdown, no code fences, no extra text.

Each object must include:
- relevance_score (0..1)
- backend_depth_score (0..1)
- novelty_score (0..1)
- actionability_score (0..1)
- linkedin_potential_score (0..1)
- final_score (0..1)
- decision ("keep" or "discard")
- reasoning_summary (short sentence <= 220 chars)

Scoring intent:
- Prefer practical backend architecture/reliability/performance insights.
- Penalize generic motivational/listicle content.

Articles:
{articles_text}
"""

    try:
        response = await client.chat.completions.create(
            model=AI_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        msg = response.choices[0].message
        if not msg or not msg.content:
            return [_default_analysis() for _ in articles]

        parsed = _parse_json_array(msg.content)
        if not parsed:
            return [_default_analysis() for _ in articles]
        if len(parsed) < len(articles):
            parsed.extend([_default_analysis() for _ in range(len(articles) - len(parsed))])
        return parsed[: len(articles)]
    except Exception:
        return [_default_analysis() for _ in articles]