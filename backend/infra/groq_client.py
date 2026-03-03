"""Groq API client: fetch facts, generate completions, and generate debate arguments."""
import json
import logging
import os
import re

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
TIMEOUT = 8.0  # Increased from 4s for reliability

logger = logging.getLogger(__name__)

# Round theme descriptions passed to the LLM for contextual generation
_ROUND_THEMES = {
    1: "opening statement — establish your core principle and why your position is fundamentally correct",
    2: "evidence round — cite data, studies, real-world examples that support your position",
    3: "tradeoff analysis — compare the costs and benefits of both positions; show the balance favors yours",
    4: "ethical argument — argue from fairness, justice, and moral responsibility",
    5: "risk analysis — highlight the dangers of the opposing position; argue for caution or urgency",
    6: "closing statement — synthesize all prior arguments into a compelling final case",
}


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return text


def _normalize_claims(values: list) -> list[str]:
    return [str(x).strip() for x in values if str(x).strip()]


async def get_facts_from_groq(topic: str) -> tuple[list[str], list[str]] | None:
    """Return (pro_claims, con_claims) from Groq, or None on any failure."""
    key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not key:
        logger.info("GROQ_API_KEY not set; using template claims")
        return None

    prompt = f'''For the debate topic "{topic}", provide factual claims only. No opinions or rhetoric.
Output a single JSON object with exactly two keys: "pro" and "con".
- "pro": array of 5 or 6 short factual sentences supporting the topic.
- "con": array of 5 or 6 short factual sentences opposing the topic.
Each claim should be one sentence. Output valid JSON only, no markdown or code fences.'''

    try:
        logger.info(f"Requesting facts from Groq for topic: {topic!r}")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
            )
        logger.info(f"Groq facts response: status={response.status_code}")
        response.raise_for_status()
        data = response.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except Exception as exc:
        logger.error(f"Groq request failed: {exc}")
        return None

    content = _strip_markdown_fence(content)

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Groq returned non-JSON content")
        return None

    pro = payload.get("pro")
    con = payload.get("con")
    if not isinstance(pro, list) or not isinstance(con, list):
        logger.warning("Groq response missing list fields 'pro' and 'con'")
        return None

    pro_claims = _normalize_claims(pro)
    con_claims = _normalize_claims(con)
    if len(pro_claims) < 2 or len(con_claims) < 2:
        logger.warning("Groq returned too few claims (pro=%s, con=%s)", len(pro_claims), len(con_claims))
        return None

    return pro_claims, con_claims


async def generate_completion(prompt: str) -> str | None:
    """
    Send a single prompt to Groq and return the text response.
    Returns None if GROQ_API_KEY is unset or the call fails.
    """
    key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not key:
        return None

    try:
        logger.info("Calling Groq for completion")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                },
            )
        response.raise_for_status()
        data = response.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content") or None
    except Exception as exc:
        logger.error(f"Groq completion failed: {exc}")
        return None


async def generate_debate_arguments(
    topic: str,
    side: str,                      # "pro" or "con"
    round_num: int,
    history_summary: str,           # pre-formatted string of recent debate turns
    pro_claims: list[str],
    con_claims: list[str],
    count: int = 4,
) -> list[dict] | None:
    """
    Generate LLM-powered debate arguments for one turn.

    Calls Groq ONCE and requests `count` structured arguments as a JSON array.
    Returns a list of dicts (claim, premises, inference, strength, reasoning_type),
    or None if Groq is unavailable or returns invalid data.

    Args:
        topic: The debate topic.
        side: "pro" or "con".
        round_num: Current debate round (1-based).
        history_summary: Recent argument history as a formatted string.
        pro_claims: Background fact claims for the pro side.
        con_claims: Background fact claims for the con side.
        count: Number of candidate arguments to generate.
    """
    key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not key:
        return None

    side_label = "FOR (Pro)" if side == "pro" else "AGAINST (Con)"
    theme = _ROUND_THEMES.get(round_num, _ROUND_THEMES[6])
    side_facts = pro_claims if side == "pro" else con_claims
    facts_snippet = "\n".join(f"- {c}" for c in side_facts[:4])

    prompt = f"""You are an expert debater arguing {side_label} the following topic:
TOPIC: "{topic}"

ROUND {round_num} THEME: {theme}

BACKGROUND FACTS FOR YOUR SIDE:
{facts_snippet}

RECENT DEBATE HISTORY:
{history_summary if history_summary else "(This is the opening round — no prior arguments yet.)"}

Your task: Generate exactly {count} distinct, high-quality debate arguments for the {side_label} side.

STRICT OUTPUT FORMAT — respond with ONLY a valid JSON array, no markdown, no explanation:
[
  {{
    "claim": "One clear, assertive sentence stating the core point",
    "premises": ["Supporting fact or evidence 1", "Supporting fact or evidence 2"],
    "inference": "One sentence explaining how the premises lead to the claim",
    "strength": <float 0.0-1.0 reflecting logical soundness and persuasive force>,
    "reasoning_type": "causal" | "ethical" | "risk" | "tradeoff" | "rebuttal" | "deductive"
  }},
  ...
]

Rules:
- Each argument must be DISTINCT — different angle, different evidence
- Arguments must be SPECIFIC to "{topic}", not generic
- If history is present, at least ONE argument should directly rebut the opponent's last point
- Strength 0.7+ = strong evidence-backed; 0.5-0.7 = moderate; below 0.5 = weak
- Keep claims under 150 characters; premises under 200 characters each"""

    try:
        logger.info(f"Requesting LLM debate arguments: topic={topic!r}, side={side}, round={round_num}")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.65,
                },
            )
        response.raise_for_status()
        data = response.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except Exception as exc:
        logger.error(f"Groq debate argument generation failed: {exc}")
        return None

    content = _strip_markdown_fence(content)

    try:
        args_raw = json.loads(content)
        if not isinstance(args_raw, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(f"LLM returned non-array JSON for debate args: {exc}")
        return None

    validated = []
    for item in args_raw:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        if not claim:
            continue
        strength = float(item.get("strength") or 0.5)
        strength = max(0.0, min(1.0, strength))
        validated.append({
            "claim": claim[:200],
            "premises": [str(p) for p in (item.get("premises") or [])[:3] if p],
            "inference": str(item.get("inference") or "")[:300],
            "strength": round(strength, 3),
            "reasoning_type": str(item.get("reasoning_type") or "causal"),
        })

    logger.info(f"LLM generated {len(validated)} debate arguments for {side}, round {round_num}")
    return validated if validated else None
