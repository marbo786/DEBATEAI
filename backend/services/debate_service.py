"""Debate orchestration use-cases independent of delivery framework."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Callable, Awaitable, AsyncGenerator

try:
    from backend.domain.belief import BeliefModel
    from backend.domain.minimax import MinimaxAgent
    from backend.domain.reasoning import ArgumentGenerator
    from backend.domain.state import DebateState, RoundRecord, Side, Argument, Persona
    from backend.infra.models import DebateRecord, RoundRecordModel
    from backend.infra.groq_client import generate_debate_arguments
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
except ModuleNotFoundError:  # Vercel backend project rooted at /backend
    from domain.belief import BeliefModel
    from domain.minimax import MinimaxAgent
    from domain.reasoning import ArgumentGenerator
    from domain.state import DebateState, RoundRecord, Side, Argument, Persona
    from infra.models import DebateRecord, RoundRecordModel
    from infra.groq_client import generate_debate_arguments
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

FactsProvider = Callable[[str], Awaitable[tuple[list[str], list[str]] | None]]

MIN_ROUNDS = 2
MAX_ROUNDS = 10


@dataclass
class DebateResult:
    state: DebateState
    pruning_logs: list[dict]
    facts_from_api: bool


class DebateService:
    """Runs complete debates and computes summaries."""

    def __init__(self, max_rounds: int = 6, seed: int | None = None) -> None:
        self.max_rounds = max_rounds
        self.arg_gen = ArgumentGenerator(seed=seed)
        self.belief_model = BeliefModel(sensitivity=0.12, prior=0.5)
        self.minimax_pro = MinimaxAgent(
            argument_generator=self.arg_gen,
            belief_model=self.belief_model,
            depth=3,
        )
        self.minimax_con = MinimaxAgent(
            argument_generator=self.arg_gen,
            belief_model=self.belief_model,
            depth=3,
        )

    async def get_debate_state(self, debate_id: str, db: AsyncSession) -> DebateState | None:
        result = await db.execute(
            select(DebateRecord)
            .where(DebateRecord.id == debate_id)
            .options(selectinload(DebateRecord.rounds))
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        return self._build_state_from_record(record)

    def _build_state_from_record(self, record: DebateRecord) -> DebateState:
        history = []
        belief_history = [0.5]
        used_claims: set = set()
        for r_rec in record.rounds:
            arg = Argument(
                claim=r_rec.claim,
                premises=r_rec.premises,
                inference=r_rec.inference,
                strength=r_rec.strength,
                reasoning_type=r_rec.reasoning_type,
            )
            history.append(RoundRecord(side=Side(r_rec.side), argument=arg, belief_after=r_rec.belief_after))
            belief_history.append(r_rec.belief_after)
            used_claims.add(r_rec.claim)
        state = DebateState(
            id=str(record.id),
            topic=record.topic,
            user_side=record.user_side,
            pro_claims=record.pro_claims,
            con_claims=record.con_claims,
            history=history,
            belief=record.belief,
            belief_history=belief_history,
            round_number=len(history),
            max_rounds=record.max_rounds,
            winner=Side(record.winner) if record.winner else None,
            used_claims=used_claims,
        )
        state.turning_point_round = self._turning_point(state)
        return state

    # ------------------------------------------------------------------ #
    #  Shared initialization helper (DRY: used by all three run methods)  #
    # ------------------------------------------------------------------ #

    async def _create_debate_record(
        self,
        topic: str,
        rounds: int,
        facts_provider: FactsProvider | None,
        persona: Persona | str,
        user_side: str,
        db: AsyncSession | None,
    ) -> tuple[DebateState, DebateRecord | None, bool]:
        """
        Resolve facts, build an initial DebateState, and optionally persist a
        DebateRecord to the database.
        """
        self.belief_model = BeliefModel.create_from_persona(persona)
        self.minimax_pro = MinimaxAgent(self.arg_gen, self.belief_model, depth=3)
        self.minimax_con = MinimaxAgent(self.arg_gen, self.belief_model, depth=3)

        max_rounds = max(MIN_ROUNDS, min(MAX_ROUNDS, rounds))
        api_facts = await facts_provider(topic) if facts_provider else None
        facts_from_api = bool(api_facts)

        if api_facts is not None:
            pro_claims, con_claims = api_facts
        else:
            pro_claims, con_claims = self.arg_gen.generate_initial_claims(topic)

        state = DebateState(
            topic=topic,
            user_side=user_side,
            pro_claims=pro_claims,
            con_claims=con_claims,
            history=[],
            belief=self.belief_model.prior,
            belief_history=[self.belief_model.prior],
            round_number=0,
            max_rounds=max_rounds,
        )

        db_debate = None
        if db:
            db_debate = DebateRecord(
                topic=topic,
                persona=persona.value if isinstance(persona, Persona) else persona,
                user_side=user_side,
                pro_claims=pro_claims,
                con_claims=con_claims,
                max_rounds=max_rounds,
                belief=self.belief_model.prior,
            )
            db.add(db_debate)
            await db.commit()
            await db.refresh(db_debate)
            state.id = str(db_debate.id)

        return state, db_debate, facts_from_api

    # ------------------------------------------------------------------ #
    #  LLM candidate generation (Phase 2)                                 #
    # ------------------------------------------------------------------ #

    async def _get_llm_candidates(self, state: DebateState, side: Side) -> list[Argument]:
        """
        Call Groq to generate extra candidate arguments for this turn.
        Returns a list of Argument objects, or empty list if Groq unavailable.
        """
        # Build a short history summary for the LLM prompt (last 3 turns)
        recent = state.history[-3:]
        if recent:
            lines = []
            for r in recent:
                speaker = "PRO" if r.side == Side.PRO else "CON"
                lines.append(f"[{speaker}]: {r.argument.claim}")
            history_summary = "\n".join(lines)
        else:
            history_summary = ""

        round_num = max(1, (state.round_number // 2) + 1)

        raw = await generate_debate_arguments(
            topic=state.topic,
            side=side.value,
            round_num=round_num,
            history_summary=history_summary,
            pro_claims=state.pro_claims,
            con_claims=state.con_claims,
            count=4,
        )
        if not raw:
            return []

        result: list[Argument] = []
        for d in raw:
            try:
                result.append(Argument(
                    claim=d["claim"],
                    premises=d.get("premises", []),
                    inference=d.get("inference", ""),
                    strength=float(d.get("strength", 0.5)),
                    reasoning_type=d.get("reasoning_type", "causal"),
                ))
            except (KeyError, ValueError):
                continue
        return result

    # ------------------------------------------------------------------ #

    async def initialize_debate(
        self,
        topic: str,
        rounds: int,
        facts_provider: FactsProvider | None = None,
        persona: Persona | str = Persona.DEFAULT,
        user_side: str = "auto",
        db: AsyncSession = None,
    ) -> DebateResult:
        state, _, facts_from_api = await self._create_debate_record(
            topic, rounds, facts_provider, persona, user_side, db
        )
        return DebateResult(
            state=state,
            pruning_logs=[],
            facts_from_api=facts_from_api,
        )

    async def run_debate(
        self,
        topic: str,
        rounds: int,
        facts_provider: FactsProvider | None = None,
        persona: Persona | str = Persona.DEFAULT,
        user_side: str = "auto",
        db: AsyncSession = None,
    ) -> DebateResult:
        state, db_debate, facts_from_api = await self._create_debate_record(
            topic, rounds, facts_provider, persona, user_side, db
        )

        pruning_logs: list[dict] = []
        for debate_round in range(state.max_rounds):
            # Get LLM candidates for PRO
            llm_pro = await self._get_llm_candidates(state, Side.PRO)
            best_pro, _ = self.minimax_pro.get_best_argument(state, Side.PRO, extra_candidates=llm_pro)
            if best_pro:
                state = await self._apply(state, Side.PRO, best_pro, db, db_debate)
                pruning_logs.append({
                    "side": "pro",
                    "round": debate_round + 1,
                    "pruning_log": self.minimax_pro.get_pruning_log_dict(),
                })

            if (state.round_number // 2) >= state.max_rounds:
                break

            # Get LLM candidates for CON
            llm_con = await self._get_llm_candidates(state, Side.CON)
            best_con, _ = self.minimax_con.get_best_argument(state, Side.CON, extra_candidates=llm_con)
            if best_con:
                state = await self._apply(state, Side.CON, best_con, db, db_debate)
                pruning_logs.append({
                    "side": "con",
                    "round": debate_round + 1,
                    "pruning_log": self.minimax_con.get_pruning_log_dict(),
                })

            if (state.round_number // 2) >= state.max_rounds:
                break

        state.winner = self._winner(state)
        state.turning_point_round = self._turning_point(state)

        if db and db_debate:
            db_debate.status = "completed"
            db_debate.winner = state.winner.value if state.winner else "tie"
            await db.commit()

        return DebateResult(state=state, pruning_logs=pruning_logs, facts_from_api=facts_from_api)

    async def run_debate_stream(
        self,
        topic: str,
        rounds: int,
        facts_provider: FactsProvider | None = None,
        persona: Persona | str = Persona.DEFAULT,
        user_side: str = "auto",
        db: AsyncSession = None,
    ) -> AsyncGenerator[str, None]:
        state, db_debate, facts_from_api = await self._create_debate_record(
            topic, rounds, facts_provider, persona, user_side, db
        )

        yield f"data: {json.dumps({'type': 'init', 'state': state.to_dict(), 'facts_from_api': facts_from_api})}\n\n"

        for debate_round in range(state.max_rounds):
            await asyncio.sleep(0.5)

            # PRO turn
            llm_pro = await self._get_llm_candidates(state, Side.PRO)
            best_pro, _ = self.minimax_pro.get_best_argument(state, Side.PRO, extra_candidates=llm_pro)
            if best_pro:
                words = best_pro.claim.split(" ")
                for word in words:
                    yield f"data: {json.dumps({'type': 'typing', 'side': 'pro', 'chunk': word + ' '})}\n\n"
                    await asyncio.sleep(0.04)
                state = await self._apply(state, Side.PRO, best_pro, db, db_debate)
                yield f"data: {json.dumps({'type': 'move', 'state': state.to_dict()})}\n\n"
                await asyncio.sleep(0.5)

            if (state.round_number // 2) >= state.max_rounds:
                break

            await asyncio.sleep(0.5)

            # CON turn
            llm_con = await self._get_llm_candidates(state, Side.CON)
            best_con, _ = self.minimax_con.get_best_argument(state, Side.CON, extra_candidates=llm_con)
            if best_con:
                words = best_con.claim.split(" ")
                for word in words:
                    yield f"data: {json.dumps({'type': 'typing', 'side': 'con', 'chunk': word + ' '})}\n\n"
                    await asyncio.sleep(0.04)
                state = await self._apply(state, Side.CON, best_con, db, db_debate)
                yield f"data: {json.dumps({'type': 'move', 'state': state.to_dict()})}\n\n"
                await asyncio.sleep(0.5)

            if (state.round_number // 2) >= state.max_rounds:
                break

        state.winner = self._winner(state)
        state.turning_point_round = self._turning_point(state)
        if db and db_debate:
            db_debate.status = "completed"
            db_debate.winner = state.winner.value if state.winner else "tie"
            await db.commit()

        yield f"data: {json.dumps({'type': 'done', 'state': state.to_dict(), 'summary': self.summarize(state)})}\n\n"

    async def run_turn_stream(
        self,
        debate_id: str,
        db: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(DebateRecord).where(DebateRecord.id == debate_id).options(selectinload(DebateRecord.rounds))
        )
        db_debate = result.scalar_one_or_none()
        if not db_debate:
            return

        state = self._build_state_from_record(db_debate)
        if (state.round_number // 2) >= state.max_rounds:
            yield f"data: {json.dumps({'type': 'done', 'state': state.to_dict(), 'summary': self.summarize(state)})}\n\n"
            return

        is_pro_turn = (state.round_number % 2 == 0)
        current_side = Side.PRO if is_pro_turn else Side.CON

        if state.user_side == current_side.value:
            yield f"data: {json.dumps({'type': 'waiting_for_user', 'state': state.to_dict()})}\n\n"
            return

        # AI's turn — use updated belief_model from persona
        self.belief_model = BeliefModel.create_from_persona(db_debate.persona)
        agent = MinimaxAgent(self.arg_gen, self.belief_model, depth=3)

        await asyncio.sleep(0.5)
        # Get LLM candidates before running minimax
        llm_candidates = await self._get_llm_candidates(state, current_side)
        best_arg, _ = agent.get_best_argument(state, current_side, extra_candidates=llm_candidates)

        if best_arg:
            words = best_arg.claim.split(" ")
            for word in words:
                yield f"data: {json.dumps({'type': 'typing', 'side': current_side.value, 'chunk': word + ' '})}\n\n"
                await asyncio.sleep(0.04)

            state = await self._apply(state, current_side, best_arg, db, db_debate)
            yield f"data: {json.dumps({'type': 'move', 'state': state.to_dict()})}\n\n"
            await asyncio.sleep(0.5)

            if (state.round_number // 2) >= state.max_rounds:
                state.winner = self._winner(state)
                state.turning_point_round = self._turning_point(state)
                db_debate.status = "completed"
                db_debate.winner = state.winner.value if state.winner else "tie"
                await db.commit()
                yield f"data: {json.dumps({'type': 'done', 'state': state.to_dict(), 'summary': self.summarize(state)})}\n\n"
            else:
                next_side = Side.PRO if state.round_number % 2 == 0 else Side.CON
                if state.user_side == next_side.value:
                    yield f"data: {json.dumps({'type': 'waiting_for_user', 'state': state.to_dict()})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'turn_complete', 'state': state.to_dict()})}\n\n"

    def summarize(self, state: DebateState, override_belief: float | None = None) -> dict:
        """
        Compute debate summary.

        override_belief: When set, replays the full argument history through a
        fresh BeliefModel initialized at this prior (0.0=con-biased, 0.5=neutral,
        1.0=pro-biased). This gives a genuine "what would have happened with a
        different audience" score rather than just hardcoding the endpoint.
        """
        if override_belief is not None:
            # Replay history through a BeliefModel at the chosen prior
            prior = max(0.0, min(1.0, override_belief))
            # Use same sensitivity as default; only the prior changes
            replay_model = BeliefModel(sensitivity=self.belief_model.sensitivity, prior=prior)
            belief = prior
            for record in state.history:
                pro_arg = record.argument if record.side == Side.PRO else None
                con_arg = record.argument if record.side == Side.CON else None
                belief = replay_model.update_from_arguments(belief, pro_arg, con_arg)
            winner = "pro" if belief > 0.5 else "con" if belief < 0.5 else "tie"
        else:
            belief = state.belief
            winner = state.winner.value if state.winner else "tie"

        return {
            "topic": state.topic,
            "winner": winner,
            "final_belief": round(belief, 4),
            "final_pro_pct": round(belief * 100, 1),
            "final_con_pct": round((1 - belief) * 100, 1),
            "turning_point_round": state.turning_point_round,
            "total_rounds": state.round_number // 2,  # moves -> debate rounds
        }

    async def _apply(
        self,
        state: DebateState,
        side: Side,
        argument: Argument,
        db: AsyncSession = None,
        db_debate: DebateRecord = None,
    ) -> DebateState:
        pro_arg = argument if side == Side.PRO else None
        con_arg = argument if side == Side.CON else None
        new_belief = self.belief_model.update_from_arguments(state.belief, pro_arg, con_arg)
        state.history.append(RoundRecord(side=side, argument=argument, belief_after=new_belief))
        state.belief = new_belief
        state.belief_history.append(new_belief)
        state.used_claims.add(argument.claim)  # Track for deduplication

        if db and db_debate:
            round_rec = RoundRecordModel(
                debate_id=db_debate.id,
                round_number=state.round_number + 1,
                side=side.value,
                claim=argument.claim,
                premises=argument.premises,
                inference=argument.inference,
                strength=argument.strength,
                reasoning_type=argument.reasoning_type,
                belief_after=new_belief,
                is_user_move=False,
            )
            db.add(round_rec)
            db_debate.belief = new_belief
            await db.commit()

        state.round_number += 1
        return state

    @staticmethod
    def _winner(state: DebateState) -> Side | None:
        if state.belief > 0.5:
            return Side.PRO
        if state.belief < 0.5:
            return Side.CON
        return None


    @staticmethod
    def _turning_point(state: DebateState) -> int | None:
        """
        Finds the round with the largest NET belief shift.

        For each complete round k (1-indexed):
          net_shift = |belief_history[2k] - belief_history[2k-2]|

        This measures how much the audience's belief actually moved across
        the full round (both PRO and CON spoke), which closely mirrors the
        net strength advantage:  net_shift ≈ sensitivity × |pro_s − con_s|.

        A round where PRO scores 0.90 and CON only 0.30 will produce a
        large net shift and be identified as the turning point.
        Rounds where both sides were equally strong cancel out and don't count.
        """
        bh = state.belief_history
        n_complete = (len(bh) - 1) // 2  # number of fully completed rounds
        if n_complete < 1:
            return None

        max_shift = 0.0
        turn_round = None
        for k in range(1, n_complete + 1):
            before = bh[2 * (k - 1)]   # belief at start of round k
            after  = bh[2 * k]          # belief at end of round k (after CON move)
            shift  = abs(after - before)
            if shift > max_shift:
                max_shift = shift
                turn_round = k
        return turn_round
