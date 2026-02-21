"""
Fetch pro/con debate facts from Groq API (free tier).
When GROQ_API_KEY is set, one request per topic returns structured pro and con claims.
"""
import json
import os
import re

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
TIMEOUT = 30.0


def get_facts_from_groq(topic: str) -> tuple[list[str], list[str]] | None:
    """
    Call Groq chat completions to get 5-6 pro and con factual claims for the debate topic.
    Returns (pro_list, con_list) on success, None on missing key, network error, or invalid response.
    """
    key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not key:
        return None

    prompt = f"""For the debate topic "{topic}", provide factual claims only. No opinions or rhetoric.
Output a single JSON object with exactly two keys: "pro" and "con".
- "pro": array of 5 or 6 short factual sentences supporting the topic.
- "con": array of 5 or 6 short factual sentences opposing the topic.
Each claim should be one sentence. Output valid JSON only, no markdown or code fences."""

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
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
        r.raise_for_status()
        data = r.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except Exception:
        return None

    # Strip markdown code block if present
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content)

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None

    pro = obj.get("pro")
    con = obj.get("con")
    if not isinstance(pro, list) or not isinstance(con, list):
        return None
    pro = [str(x).strip() for x in pro if x]
    con = [str(x).strip() for x in con if x]
    if len(pro) < 2 or len(con) < 2:
        return None
    return (pro, con)
