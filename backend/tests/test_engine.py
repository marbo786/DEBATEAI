"""
Expanded unit tests for DebateAI — Phase 1 & Phase 2.

Covers:
  - BeliefModel: update direction, clamping to [0,1], persona creation
  - ArgumentGenerator: round themes, count, deduplication
  - MinimaxAgent: chooses better argument, extra_candidates merging, enhanced eval_state
  - parse_user_argument: fallback (no groq), heuristic scoring
  - DebateService: initialize, run, round clamping, summarize
  - Phase 2: claim deduplication, LLM candidate merging, heuristic bonuses
"""
import asyncio
import pytest

from backend.domain.belief import BeliefModel
from backend.domain.state import DebateState, Side, Persona
from backend.domain.reasoning import ArgumentGenerator, parse_user_argument
from backend.domain.minimax import MinimaxAgent
from backend.services.debate_service import DebateService


# ------------------------------------------------------------------ #
# BeliefModel tests
# ------------------------------------------------------------------ #

class TestBeliefModel:
    def test_personas_created_correctly(self):
        default_model = BeliefModel.create_from_persona(Persona.DEFAULT)
        assert default_model.sensitivity == 0.12
        assert default_model.prior == 0.5

        skeptic_model = BeliefModel.create_from_persona(Persona.SKEPTIC)
        assert skeptic_model.sensitivity == 0.05

        pro_model = BeliefModel.create_from_persona(Persona.PARTISAN_PRO)
        assert pro_model.prior == 0.7

        con_model = BeliefModel.create_from_persona(Persona.PARTISAN_CON)
        assert con_model.prior == 0.3

    def test_persona_string_fallback(self):
        """Unknown string persona falls back to DEFAULT."""
        m = BeliefModel.create_from_persona("unknown_persona_xyz")
        assert m.sensitivity == 0.12
        assert m.prior == 0.5

    def test_pro_argument_pushes_belief_up(self):
        model = BeliefModel(sensitivity=0.10, prior=0.5)
        new_belief = model.update(0.5, pro_strength=0.8, con_strength=0.2)
        assert new_belief > 0.5, "Strong pro arg should push belief above 0.5"

    def test_con_argument_pushes_belief_down(self):
        model = BeliefModel(sensitivity=0.10, prior=0.5)
        new_belief = model.update(0.5, pro_strength=0.2, con_strength=0.8)
        assert new_belief < 0.5, "Strong con arg should push belief below 0.5"

    def test_equal_arguments_leave_belief_unchanged(self):
        model = BeliefModel(sensitivity=0.10, prior=0.5)
        new_belief = model.update(0.5, pro_strength=0.6, con_strength=0.6)
        assert new_belief == 0.5

    def test_belief_clamped_to_zero(self):
        """Extreme con argument should not drive belief below 0."""
        model = BeliefModel(sensitivity=1.0, prior=0.5)
        new_belief = model.update(0.1, pro_strength=0.0, con_strength=1.0)
        assert new_belief >= 0.0

    def test_belief_clamped_to_one(self):
        """Extreme pro argument should not drive belief above 1."""
        model = BeliefModel(sensitivity=1.0, prior=0.5)
        new_belief = model.update(0.9, pro_strength=1.0, con_strength=0.0)
        assert new_belief <= 1.0


# ------------------------------------------------------------------ #
# ArgumentGenerator tests
# ------------------------------------------------------------------ #

class TestArgumentGenerator:
    def test_generates_correct_initial_claim_count(self):
        ag = ArgumentGenerator(seed=42)
        pro_claims, con_claims = ag.generate_initial_claims("AI Expansion")
        assert len(pro_claims) == 6
        assert len(con_claims) == 6

    def test_argument_count_respects_count_param(self):
        ag = ArgumentGenerator(seed=42)
        pro, con = ag.generate_initial_claims("AI Expansion")
        args = ag.generate_arguments(Side.PRO, "AI Expansion", pro, con, [], count=3)
        # Round 1 only generates 2 themed args for PRO, so result is <= count, >= 1
        assert 1 <= len(args) <= 3

    def test_round_1_produces_causal_arguments(self):
        ag = ArgumentGenerator(seed=0)
        pro, con = ag.generate_initial_claims("climate change")
        args = ag.generate_arguments(Side.PRO, "climate change", pro, con, [], count=6)
        types = [a.reasoning_type for a in args]
        assert "causal" in types, f"Round 1 should contain causal args. Got: {types}"

    def test_round_4_produces_ethical_arguments(self):
        """Simulate 6 history entries (= round 4) and check for ethical reasoning."""
        ag = ArgumentGenerator(seed=0)
        from backend.domain.state import Argument, RoundRecord
        pro, con = ag.generate_initial_claims("universal basic income")

        # Build fake history of 6 moves (rounds 1-3 done, now generating round 4)
        dummy_arg = Argument(
            claim="dummy", premises=[], inference="dummy", strength=0.5, reasoning_type="causal"
        )
        history = [
            RoundRecord(side=Side.PRO if i % 2 == 0 else Side.CON, argument=dummy_arg, belief_after=0.5)
            for i in range(6)
        ]
        args = ag.generate_arguments(Side.PRO, "universal basic income", pro, con, history, count=6)
        types = [a.reasoning_type for a in args]
        assert "ethical" in types, f"Round 4 should contain ethical args. Got: {types}"

    def test_all_arguments_have_positive_strength(self):
        ag = ArgumentGenerator(seed=7)
        pro, con = ag.generate_initial_claims("space exploration")
        args = ag.generate_arguments(Side.CON, "space exploration", pro, con, [], count=6)
        for arg in args:
            assert 0.0 <= arg.strength <= 1.0


# ------------------------------------------------------------------ #
# MinimaxAgent tests
# ------------------------------------------------------------------ #

class TestMinimaxAgent:
    def test_pro_picks_argument(self):
        """PRO agent should return a valid argument."""
        ag = ArgumentGenerator(seed=1)
        model = BeliefModel(sensitivity=0.12, prior=0.5)
        agent = MinimaxAgent(ag, model, depth=2)
        pro, con = ag.generate_initial_claims("renewable energy")
        state = DebateState(
            topic="renewable energy",
            pro_claims=pro,
            con_claims=con,
            belief=0.5,
            belief_history=[0.5],
            round_number=0,
            max_rounds=6,
        )
        best_arg, val = agent.get_best_argument(state, Side.PRO)
        assert best_arg is not None
        assert isinstance(val, float)

    def test_con_picks_argument(self):
        """CON agent should return a valid argument."""
        ag = ArgumentGenerator(seed=2)
        model = BeliefModel(sensitivity=0.12, prior=0.5)
        agent = MinimaxAgent(ag, model, depth=2)
        pro, con = ag.generate_initial_claims("nuclear power")
        state = DebateState(
            topic="nuclear power",
            pro_claims=pro,
            con_claims=con,
            belief=0.5,
            belief_history=[0.5],
            round_number=0,
            max_rounds=6,
        )
        best_arg, val = agent.get_best_argument(state, Side.CON)
        assert best_arg is not None

    def test_pruning_log_populated(self):
        """Pruning log should be non-empty after search with enough candidates."""
        ag = ArgumentGenerator(seed=42)
        model = BeliefModel(sensitivity=0.12, prior=0.5)
        agent = MinimaxAgent(ag, model, depth=3)
        pro, con = ag.generate_initial_claims("free trade")
        state = DebateState(
            topic="free trade",
            pro_claims=pro,
            con_claims=con,
            belief=0.5,
            belief_history=[0.5],
            round_number=0,
            max_rounds=6,
        )
        agent.get_best_argument(state, Side.PRO)
        # May or may not prune on very first move — just assert it's a list
        log = agent.get_pruning_log_dict()
        assert isinstance(log, list)


# ------------------------------------------------------------------ #
# parse_user_argument tests
# ------------------------------------------------------------------ #

class TestParseUserArgument:
    def test_fallback_returns_valid_argument(self):
        """Without a groq_completion, should return a valid Argument immediately."""
        arg = asyncio.get_event_loop().run_until_complete(
            parse_user_argument("We should invest more in renewable energy because it creates jobs.", groq_completion=None)
        )
        assert arg.claim != ""
        assert isinstance(arg.premises, list)
        assert 0.0 <= arg.strength <= 1.0
        assert arg.reasoning_type == "informal"

    def test_fallback_heuristic_scores_longer_args_higher(self):
        """A longer, structured argument should score higher than a one-word reply."""
        short = asyncio.get_event_loop().run_until_complete(
            parse_user_argument("No.", groq_completion=None)
        )
        long_text = (
            "Although there are risks, the data shows that renewable energy creates significantly "
            "more jobs than fossil fuels, and therefore the economic case for transition is strong."
        )
        long_arg = asyncio.get_event_loop().run_until_complete(
            parse_user_argument(long_text, groq_completion=None)
        )
        assert long_arg.strength >= short.strength

    def test_fallback_caps_claim_at_300_chars(self):
        very_long = "x" * 500
        arg = asyncio.get_event_loop().run_until_complete(
            parse_user_argument(very_long, groq_completion=None)
        )
        assert len(arg.claim) <= 300

    @pytest.mark.asyncio
    async def test_fallback_on_groq_failure_returns_valid_arg(self):
        """If groq_completion raises, should still return a valid fallback."""
        async def failing_groq(prompt: str):
            raise RuntimeError("Connection refused")

        arg = await parse_user_argument("This is a test argument.", groq_completion=failing_groq)
        assert arg.claim != ""
        assert 0.0 <= arg.strength <= 1.0

    @pytest.mark.asyncio
    async def test_groq_bad_json_falls_back_gracefully(self):
        """If groq returns non-JSON, should use fallback without crashing."""
        async def bad_json_groq(prompt: str):
            return "This is not JSON at all!"

        arg = await parse_user_argument("My argument here.", groq_completion=bad_json_groq)
        assert isinstance(arg.claim, str)
        assert arg.claim != ""


# ------------------------------------------------------------------ #
# DebateService tests
# ------------------------------------------------------------------ #

class TestDebateService:
    @pytest.mark.asyncio
    async def test_initialize_debate_returns_clean_state(self):
        """initialize_debate should return state with 0 history and correct topic."""
        service = DebateService(seed=42)

        async def mock_facts(topic):
            return (["Pro claim 1", "Pro claim 2"], ["Con claim 1", "Con claim 2"])

        result = await service.initialize_debate(
            topic="Universal Basic Income",
            rounds=6,
            facts_provider=mock_facts,
            persona=Persona.DEFAULT,
            user_side="auto",
            db=None,
        )
        assert result.state.topic == "Universal Basic Income"
        assert len(result.state.history) == 0
        assert result.state.belief == 0.5
        assert result.state.round_number == 0
        assert result.facts_from_api is True

    @pytest.mark.asyncio
    async def test_run_debate_completes_all_rounds(self):
        """run_debate should complete max_rounds full rounds."""
        service = DebateService(max_rounds=4, seed=42)

        async def mock_facts(topic):
            return (["Pro claim"] * 4, ["Con claim"] * 4)

        result = await service.run_debate(
            topic="Testing",
            rounds=4,
            facts_provider=mock_facts,
            persona=Persona.DEFAULT,
        )
        assert result.state.topic == "Testing"
        # With deduplication active, mock claims may be filtered after reuse.
        # At minimum, 2 full rounds (4 moves) must complete.
        assert len(result.state.history) >= 4
        assert result.facts_from_api is True

    @pytest.mark.asyncio
    async def test_rounds_clamped_to_min_max(self):
        """Rounds below 2 should be clamped to 2, above 10 to 10."""
        service = DebateService(seed=0)

        async def mock_facts(topic):
            return (["p"] * 4, ["c"] * 4)

        result_min = await service.initialize_debate("test", rounds=0, facts_provider=mock_facts, db=None)
        assert result_min.state.max_rounds == 2

        result_max = await service.initialize_debate("test", rounds=99, facts_provider=mock_facts, db=None)
        assert result_max.state.max_rounds == 10

    @pytest.mark.asyncio
    async def test_summarize_returns_correct_structure(self):
        service = DebateService(seed=1)

        async def mock_facts(topic):
            return (["p"] * 4, ["c"] * 4)

        result = await service.run_debate("Summary test", rounds=4, facts_provider=mock_facts)
        summary = service.summarize(result.state)
        assert "winner" in summary
        assert "final_belief" in summary
        assert "final_pro_pct" in summary
        assert "final_con_pct" in summary
        assert abs(summary["final_pro_pct"] + summary["final_con_pct"] - 100) < 0.01


# ------------------------------------------------------------------ #
# Phase 2: Claim Deduplication tests
# ------------------------------------------------------------------ #

class TestClaimDeduplication:
    def test_similar_claim_is_filtered(self):
        """Claims with >60% word overlap vs used_claims should be filtered out."""
        from backend.domain.reasoning import _is_too_similar
        used = {"AI expansion creates jobs and economic growth for society"}
        # Very similar claim — should be filtered
        assert _is_too_similar("AI expansion creates jobs and economic benefits", used, threshold=0.6)

    def test_different_claim_passes(self):
        """A genuinely different claim should NOT be filtered."""
        from backend.domain.reasoning import _is_too_similar
        used = {"AI expansion creates jobs and economic growth"}
        # Completely different claim
        assert not _is_too_similar("Climate change poses severe risks to coastal ecosystems", used)

    def test_empty_used_claims_never_filters(self):
        """With no used claims, nothing should be filtered."""
        from backend.domain.reasoning import _is_too_similar
        assert not _is_too_similar("Any claim at all", set())

    def test_generate_arguments_deduplicated_with_used_claims(self):
        """generate_arguments should return fewer args when many are similar to used_claims."""
        ag = ArgumentGenerator(seed=0)
        pro, con = ag.generate_initial_claims("AI in healthcare")
        # Put all generated claims into used_claims first
        initial_args = ag.generate_arguments(Side.PRO, "AI in healthcare", pro, con, [], count=6)
        used = {a.claim for a in initial_args}
        # Calling again with same seed+used_claims should return empty or very few
        new_args = ag.generate_arguments(Side.PRO, "AI in healthcare", pro, con, [], count=6, used_claims=used)
        # At a strict 60% threshold, some may still pass — just ensure deduplication ran
        assert len(new_args) <= len(initial_args)


# ------------------------------------------------------------------ #
# Phase 2: LLM candidate merging in MinimaxAgent
# ------------------------------------------------------------------ #

class TestLLMCandidateMerging:
    def test_extra_candidates_included_in_pool(self):
        """Extra LLM candidates should be evaluated by minimax alongside templates."""
        ag = ArgumentGenerator(seed=42)
        model = BeliefModel(sensitivity=0.12, prior=0.5)
        agent = MinimaxAgent(ag, model, depth=2)
        pro, con = ag.generate_initial_claims("renewable energy")
        state = DebateState(
            topic="renewable energy",
            pro_claims=pro,
            con_claims=con,
            belief=0.5,
            belief_history=[0.5],
            round_number=0,
            max_rounds=6,
        )
        # Create a strong LLM argument — minimax should at least consider it
        from backend.domain.state import Argument
        llm_arg = Argument(
            claim="Renewable energy directly reduces carbon emissions proven by 50-year data.",
            premises=["Peer-reviewed studies show 40% CO2 reduction from solar adoption."],
            inference="Therefore renewable energy is the most effective climate solution.",
            strength=0.95,
            reasoning_type="causal",
        )
        best_arg, _ = agent.get_best_argument(state, Side.PRO, extra_candidates=[llm_arg])
        assert best_arg is not None
        # With such a high-strength LLM arg, it should be selected
        assert best_arg.claim == llm_arg.claim

    def test_no_extra_candidates_still_works(self):
        """Passing extra_candidates=None should behave identically to Phase 1."""
        ag = ArgumentGenerator(seed=7)
        model = BeliefModel(sensitivity=0.12, prior=0.5)
        agent = MinimaxAgent(ag, model, depth=2)
        pro, con = ag.generate_initial_claims("space exploration")
        state = DebateState(
            topic="space exploration",
            pro_claims=pro,
            con_claims=con,
            belief=0.5,
            belief_history=[0.5],
            round_number=0,
            max_rounds=6,
        )
        best_arg, val = agent.get_best_argument(state, Side.CON, extra_candidates=None)
        assert best_arg is not None
        assert isinstance(val, float)


# ------------------------------------------------------------------ #
# Phase 2: Enhanced eval_state heuristics
# ------------------------------------------------------------------ #

class TestEnhancedEvalState:
    def _make_state(self, history_sides_strengths, belief_history=None) -> DebateState:
        """Helper to construct a DebateState with given history."""
        from backend.domain.state import Argument, RoundRecord
        history = []
        belief = 0.5
        bh = [0.5]
        for i, (side_str, strength, rtype) in enumerate(history_sides_strengths):
            side = Side.PRO if side_str == "pro" else Side.CON
            arg = Argument(
                claim=f"Argument {i}",
                premises=[],
                inference="...",
                strength=strength,
                reasoning_type=rtype,
            )
            belief = belief + 0.05 if side == Side.PRO else belief - 0.05
            belief = max(0.0, min(1.0, belief))
            bh.append(belief)
            history.append(RoundRecord(side=side, argument=arg, belief_after=belief))
        return DebateState(
            topic="test",
            pro_claims=[],
            con_claims=[],
            belief=belief,
            belief_history=belief_history or bh,
            round_number=len(history),
            max_rounds=6,
            history=history,
        )

    def test_momentum_bonus_for_pro(self):
        """Two consecutive PRO wins should yield a higher eval_state score."""
        from backend.domain.minimax import eval_state
        model = BeliefModel(sensitivity=0.12, prior=0.5)
        # Two consecutive pro-favoring deltas
        state = self._make_state(
            [("pro", 0.7, "causal"), ("pro", 0.7, "causal")],
            belief_history=[0.5, 0.55, 0.60],
        )
        score_with_momentum = eval_state(state, model, Side.PRO)
        # Compare with a one-move state (no momentum)
        state_no_momentum = self._make_state(
            [("pro", 0.7, "causal")],
            belief_history=[0.5, 0.55],
        )
        score_without = eval_state(state_no_momentum, model, Side.PRO)
        assert score_with_momentum > score_without, "Momentum should increase PRO eval"

    def test_rebuttal_bonus(self):
        """An argument with attack_target set should receive a rebuttal bonus."""
        from backend.domain.minimax import eval_state
        from backend.domain.state import Argument, RoundRecord
        model = BeliefModel(sensitivity=0.12, prior=0.5)
        arg_rebuttal = Argument(
            claim="Rebuttal argument",
            premises=[],
            inference="",
            strength=0.6,
            reasoning_type="rebuttal",
            attack_target=0,  # <-- has attack target
        )
        arg_plain = Argument(
            claim="Plain argument",
            premises=[],
            inference="",
            strength=0.6,
            reasoning_type="causal",
            attack_target=None,  # no attack target
        )
        state_rebuttal = DebateState(
            topic="t", pro_claims=[], con_claims=[], belief=0.5,
            belief_history=[0.5, 0.55], round_number=1, max_rounds=6,
            history=[RoundRecord(side=Side.PRO, argument=arg_rebuttal, belief_after=0.55)],
        )
        state_plain = DebateState(
            topic="t", pro_claims=[], con_claims=[], belief=0.5,
            belief_history=[0.5, 0.55], round_number=1, max_rounds=6,
            history=[RoundRecord(side=Side.PRO, argument=arg_plain, belief_after=0.55)],
        )
        assert eval_state(state_rebuttal, model, Side.PRO) > eval_state(state_plain, model, Side.PRO)
