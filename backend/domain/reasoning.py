"""
Logical reasoning layer: round-aware, non-repetitive argument generation.
Each round uses different themes (opening, evidence, rebuttal, tradeoff, risk, conclusion).
Arguments reference the opponent's last claim when available.
Initial claims come from the caller (e.g. Groq API in app) or generic templates here.
"""
import random
from .state import Argument, RoundRecord, Side, ReasoningType


def _is_too_similar(claim: str, used_claims: set, threshold: float = 0.60) -> bool:
    """
    Returns True if `claim` has >threshold Jaccard word-overlap with any used claim.
    Used to prevent the same argument from appearing multiple times across rounds.
    """
    words = set(claim.lower().split())
    # Remove very common stop words so overlap is content-based
    stop = {"the", "a", "an", "is", "are", "of", "and", "to", "in", "that",
            "it", "for", "on", "with", "as", "by", "this", "from", "or"}
    words -= stop
    if not words:
        return False
    for used in used_claims:
        used_words = set(used.lower().split()) - stop
        if not used_words:
            continue
        intersection = words & used_words
        union = words | used_words
        if union and len(intersection) / len(union) >= threshold:
            return True
    return False


def _last_opponent_record(history: list, side: Side):
    for i in range(len(history) - 1, -1, -1):
        if history[i].side != side:
            return history[i], i
    return None, None


def _current_round(history_len: int) -> int:
    return (history_len // 2) + 1


class ArgumentGenerator:
    """
    Generates structured arguments that vary by round and reference the debate.
    No external APIs; single reasoning system; deterministic given seed.
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def generate_initial_claims(self, topic: str) -> tuple[list[str], list[str]]:
        """
        Produce initial claims per side. Used when no API facts were provided; generic templates only.
        """
        pro = [
            f"Supporting {topic} leads to measurable benefits for society.",
            f"Evidence shows that {topic} improves outcomes when implemented well.",
            f"Ethical and practical considerations favor adopting {topic}.",
            f"Long-term gains from {topic} outweigh short-term costs.",
            f"Implementation of {topic} is feasible and has precedent elsewhere.",
            f"Fairness and access improve under policies that support {topic}.",
        ]
        con = [
            f"Opposing {topic} is justified by significant risks and costs.",
            f"Implementing {topic} creates unintended negative consequences.",
            f"Alternatives to {topic} offer better tradeoffs.",
            f"Evidence on {topic} is mixed; caution is warranted.",
            f"Resource and practical constraints make {topic} difficult to sustain.",
            f"Risks of {topic} fall disproportionately on vulnerable groups.",
        ]
        return pro, con

    def generate_arguments(
        self,
        side: Side,
        topic: str,
        pro_claims: list[str],
        con_claims: list[str],
        history: list,
        count: int = 6,
        used_claims: set | None = None,
    ) -> list[Argument]:
        """
        Generate candidate arguments. Content varies by current round and
        references the opponent's last argument when present.
        Filters out arguments whose claims are too similar to already-used claims.
        """
        claims = pro_claims if side == Side.PRO else con_claims
        opp_claims = con_claims if side == Side.PRO else pro_claims
        history = history or []
        round_num = _current_round(len(history))
        last_opp, opp_index = _last_opponent_record(history, side)
        args = []

        # Rebuttal: explicitly address opponent's last claim (when available)
        if last_opp is not None and last_opp.argument:
            rebut = self._rebuttal_argument(
                side, topic, last_opp.argument.claim, claims, opp_claims, opp_index
            )
            if rebut:
                args.append(rebut)

        # Round-themed arguments (different content each round)
        args.extend(
            self._round_themed_arguments(
                side, topic, claims, opp_claims, round_num, last_opp
            )
        )

        self._rng.shuffle(args)

        # Deduplication: filter claims too similar to already-used ones
        if used_claims:
            args = [a for a in args if not _is_too_similar(a.claim, used_claims)]

        return args[:count]



    def _rebuttal_argument(
        self,
        side: Side,
        topic: str,
        opponent_claim: str,
        claims: list[str],
        opp_claims: list[str],
        attack_index: int,
    ) -> Argument | None:
        """Build an argument that directly counters the opponent's stated claim."""
        if not claims:
            return None
        # Shorten opponent claim for premise if very long
        opp_ref = (
            opponent_claim[:120] + "..."
            if len(opponent_claim) > 120
            else opponent_claim
        )
        if side == Side.PRO:
            premises = [
                f"The opposition argued that: \"{opp_ref}\".",
                "This overlooks key evidence and causal links.",
                claims[self._rng.randint(0, len(claims) - 1)],
            ]
            claim = (
                f"Contrary to the opposition's point, supporting {topic} is still the better choice."
            )
            inference = "Rebuttal: the opponent's claim does not hold under closer analysis; our position stands."
        else:
            premises = [
                f"The opposition argued that: \"{opp_ref}\".",
                "This overstates benefits and understates costs and risks.",
                claims[self._rng.randint(0, len(claims) - 1)],
            ]
            claim = (
                f"Contrary to the opposition's point, opposing {topic} remains justified."
            )
            inference = "Rebuttal: the opponent's claim is flawed; the counter-position is stronger."
        strength = 0.55 + self._rng.uniform(0, 0.25)
        return Argument(
            claim=claim,
            premises=premises,
            inference=inference,
            attack_target=attack_index,
            strength=min(1.0, strength),
            reasoning_type="rebuttal",
        )

    def _round_themed_arguments(
        self,
        side: Side,
        topic: str,
        claims: list[str],
        opp_claims: list[str],
        round_num: int,
        last_opp: RoundRecord | None,
    ) -> list[Argument]:
        """Generate arguments whose wording and focus depend on the round number."""
        out = []
        # Use different claim indices so each round uses different content
        c_idx = (round_num - 1) % max(1, len(claims))
        c = claims[c_idx]
        c_alt = claims[(c_idx + 1) % len(claims)] if len(claims) > 1 else c

        # Round 1: Opening / principle
        if round_num == 1:
            if side == Side.PRO:
                premises = [
                    f"On the question of {topic}, the central principle is benefit to the many.",
                    c,
                    "First principles support moving forward.",
                ]
                inference = "From principle, we conclude that adoption is justified."
            else:
                premises = [
                    f"On the question of {topic}, the central principle is avoiding harm.",
                    c,
                    "First principles support caution.",
                ]
                inference = "From principle, we conclude that opposition is justified."
            out.append(
                Argument(
                    claim=c,
                    premises=premises,
                    inference=inference,
                    attack_target=None,
                    strength=0.5 + self._rng.uniform(0, 0.2),
                    reasoning_type=ReasoningType.CAUSAL.value,
                )
            )
            # Second opening variant
            if side == Side.PRO:
                out.append(
                    Argument(
                        claim=c_alt,
                        premises=[
                            f"A practical framing of {topic} shows clear advantages.",
                            c_alt,
                            "The opening position is therefore strong.",
                        ],
                        inference="From an opening principle, we support this claim.",
                        attack_target=None,
                        strength=0.48 + self._rng.uniform(0, 0.22),
                        reasoning_type=ReasoningType.CAUSAL.value,
                    )
                )
            else:
                out.append(
                    Argument(
                        claim=c_alt,
                        premises=[
                            f"A practical framing of {topic} reveals serious drawbacks.",
                            c_alt,
                            "The opening position is therefore one of opposition.",
                        ],
                        inference="From an opening principle, we oppose this policy.",
                        attack_target=None,
                        strength=0.48 + self._rng.uniform(0, 0.22),
                        reasoning_type=ReasoningType.CAUSAL.value,
                    )
                )

        # Round 2: Evidence / data
        if round_num == 2:
            premises = [
                f"Empirical evidence regarding {topic} points in a clear direction.",
                "Data and studies support the following.",
                c,
            ]
            inference = "Evidence-based reasoning supports this claim."
            out.append(
                Argument(
                    claim=c,
                    premises=premises,
                    inference=inference,
                    attack_target=None,
                    strength=0.52 + self._rng.uniform(0, 0.22),
                    reasoning_type=ReasoningType.CAUSAL.value,
                )
            )
            out.append(
                Argument(
                    claim=c_alt,
                    premises=[
                        f"Further evidence on {topic} reinforces the direction we support.",
                        c_alt,
                        "Data and precedent align with this view.",
                    ],
                    inference="Additional evidence supports this claim.",
                    attack_target=None,
                    strength=0.5 + self._rng.uniform(0, 0.2),
                    reasoning_type=ReasoningType.CAUSAL.value,
                )
            )

        # Round 3: Contrast with opponent (if we have one) or tradeoff
        if round_num == 3:
            premises = [
                f"Weighing {topic} requires comparing both sides.",
                c,
                "The balance of considerations favors our position.",
            ]
            inference = "Tradeoff reasoning leads to our conclusion."
            out.append(
                Argument(
                    claim=c,
                    premises=premises,
                    inference=inference,
                    attack_target=None,
                    strength=0.5 + self._rng.uniform(0, 0.25),
                    reasoning_type=ReasoningType.TRADEOFF.value,
                )
            )
            out.append(
                Argument(
                    claim=c_alt,
                    premises=[
                        f"Comparing benefits and costs of {topic} yields a clear verdict.",
                        c_alt,
                        "The tradeoff favors our side.",
                    ],
                    inference="Tradeoff analysis supports our position.",
                    attack_target=None,
                    strength=0.48 + self._rng.uniform(0, 0.24),
                    reasoning_type=ReasoningType.TRADEOFF.value,
                )
            )

        # Round 4: Ethical / fairness
        if round_num == 4:
            premises = [
                f"Ethical analysis of {topic} must consider fairness and welfare.",
                "The morally defensible position aligns with the following.",
                c,
            ]
            inference = "Ethical reasoning supports this claim."
            out.append(
                Argument(
                    claim=c,
                    premises=premises,
                    inference=inference,
                    attack_target=None,
                    strength=0.48 + self._rng.uniform(0, 0.28),
                    reasoning_type=ReasoningType.ETHICAL.value,
                )
            )
            out.append(
                Argument(
                    claim=c_alt,
                    premises=[
                        f"Fairness and welfare in the context of {topic} point one way.",
                        c_alt,
                        "The ethical conclusion is clear.",
                    ],
                    inference="Ethical reasoning supports this conclusion.",
                    attack_target=None,
                    strength=0.5 + self._rng.uniform(0, 0.22),
                    reasoning_type=ReasoningType.ETHICAL.value,
                )
            )

        # Round 5: Risk
        if round_num == 5:
            if side == Side.PRO:
                premises = [
                    f"The risks of not acting on {topic} are substantial.",
                    "Delay or inaction carries its own probability of harm.",
                    c,
                ]
                claim = c
            else:
                premises = [
                    f"The risks of adopting {topic} are substantial.",
                    "Uncertainty and unintended effects favor caution.",
                    c,
                ]
                claim = c
            inference = "Risk analysis supports this position."
            out.append(
                Argument(
                    claim=claim,
                    premises=premises,
                    inference=inference,
                    attack_target=None,
                    strength=0.52 + self._rng.uniform(0, 0.2),
                    reasoning_type=ReasoningType.RISK.value,
                )
            )
            if side == Side.PRO:
                out.append(
                    Argument(
                        claim=c_alt,
                        premises=[
                            f"Inaction on {topic} carries measurable risk.",
                            c_alt,
                            "Risk analysis therefore supports moving forward.",
                        ],
                        inference="Risk reasoning favors our position.",
                        attack_target=None,
                        strength=0.5 + self._rng.uniform(0, 0.22),
                        reasoning_type=ReasoningType.RISK.value,
                    )
                )
            else:
                out.append(
                    Argument(
                        claim=c_alt,
                        premises=[
                            f"Action on {topic} carries measurable risk.",
                            c_alt,
                            "Risk analysis therefore supports caution.",
                        ],
                        inference="Risk reasoning favors our position.",
                        attack_target=None,
                        strength=0.5 + self._rng.uniform(0, 0.22),
                        reasoning_type=ReasoningType.RISK.value,
                    )
                )

        # Round 6: Conclusion / summary
        if round_num >= 6:
            premises = [
                f"Across principles, evidence, tradeoffs, and risk, the case is clear.",
                c,
                "We conclude that our position is the stronger one.",
            ]
            inference = "Cumulative reasoning supports our conclusion."
            out.append(
                Argument(
                    claim=c,
                    premises=premises,
                    inference=inference,
                    attack_target=None,
                    strength=0.5 + self._rng.uniform(0, 0.25),
                    reasoning_type=ReasoningType.ETHICAL.value,
                )
            )
            out.append(
                Argument(
                    claim=c_alt,
                    premises=[
                        f"Summing up the case on {topic}: the weight of argument is clear.",
                        c_alt,
                        "We rest our case on this conclusion.",
                    ],
                    inference="Cumulative reasoning supports our final position.",
                    attack_target=None,
                    strength=0.48 + self._rng.uniform(0, 0.26),
                    reasoning_type=ReasoningType.TRADEOFF.value,
                )
            )

        # Ensure at least one causal and one other type if we have few rounds
        if round_num <= 2 and not any(a.reasoning_type == ReasoningType.CAUSAL.value for a in out):
            premises = [
                f"Policy and evidence show a cause-effect relationship regarding {topic}.",
                c,
            ]
            out.append(
                Argument(
                    claim=c,
                    premises=premises,
                    inference="Therefore, by causal reasoning, the stated claim holds.",
                    attack_target=None,
                    strength=0.5 + self._rng.uniform(0, 0.2),
                    reasoning_type=ReasoningType.CAUSAL.value,
                )
            )

        return out


async def parse_user_argument(
    text: str,
    groq_completion=None,
) -> Argument:
    """
    Parse a raw user argument string into a structured Argument.

    If `groq_completion` is an async callable (e.g. groq_client.generate_completion),
    it is used to semantically extract claim / premises / strength via LLM.
    Without it, a sensible fallback Argument is returned immediately.

    Args:
        text: Raw user-submitted argument text.
        groq_completion: Optional async callable(prompt: str) -> str | None.

    Returns:
        Structured Argument with claim, premises, inference, strength, reasoning_type.
    """
    import json as _json

    prompt = f"""Analyze the following debate argument and extract its logical structure.
Return ONLY a valid JSON object — no markdown, no code fences — with these exact keys:
{{
  "claim": "The core point being made (one concise sentence)",
  "premises": ["Supporting premise 1", "Supporting premise 2"],
  "inference": "Brief explanation of how premises lead to the claim",
  "strength": <float 0.0-1.0 expressing logical coherence and persuasive quality>,
  "reasoning_type": "causal" | "ethical" | "risk" | "tradeoff" | "deductive" | "inductive" | "rebuttal"
}}

Argument to analyze:
\"{text}\"
"""

    if groq_completion is not None:
        try:
            raw = await groq_completion(prompt)
            if raw:
                # Strip any accidental markdown fences
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = _json.loads(raw)
                strength = max(0.0, min(1.0, float(data.get("strength", 0.5))))
                return Argument(
                    claim=str(data.get("claim") or text)[:300],
                    premises=[str(p) for p in (data.get("premises") or [])[:4]],
                    inference=str(data.get("inference") or "User argument parsed by AI."),
                    strength=strength,
                    reasoning_type=str(data.get("reasoning_type") or "informal"),
                )
        except Exception:
            pass  # Fall through to cheap fallback

    # Fallback: construct a minimal but valid Argument from the raw text
    words = text.split()
    # Heuristic strength: longer, punctuated arguments score slightly higher
    has_because = any(w.lower() in ("because", "since", "therefore", "however", "although") for w in words)
    strength = min(0.75, 0.35 + (len(words) / 200) + (0.1 if has_because else 0.0))
    return Argument(
        claim=text[:300] if len(text) <= 300 else text[:297] + "...",
        premises=["User-provided reasoning."],
        inference="Argument submitted directly by the user.",
        strength=round(strength, 3),
        reasoning_type="informal",
    )
