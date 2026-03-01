"""Fetch pro/con debate facts from Groq API."""
import json
import logging
import os
import re

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
TIMEOUT = 30.0

logger = logging.getLogger(__name__)


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
        response.raise_for_status()
        data = response.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except Exception as exc:
        logger.warning("Groq request failed: %s", exc)
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
