import pytest
import asyncio
from backend.domain.belief import BeliefModel
from backend.domain.state import DebateState, Side, Persona
from backend.domain.reasoning import ArgumentGenerator
from backend.domain.minimax import MinimaxAgent
from backend.services.debate_service import DebateService

def test_belief_model_personas():
    default_model = BeliefModel.create_from_persona(Persona.DEFAULT)
    assert default_model.sensitivity == 0.12
    assert default_model.prior == 0.5
    
    skeptic_model = BeliefModel.create_from_persona(Persona.SKEPTIC)
    assert skeptic_model.sensitivity == 0.05
    
    pro_model = BeliefModel.create_from_persona(Persona.PARTISAN_PRO)
    assert pro_model.prior == 0.7
    
    con_model = BeliefModel.create_from_persona(Persona.PARTISAN_CON)
    assert con_model.prior == 0.3

def test_argument_generator():
    ag = ArgumentGenerator(seed=42)
    pro_claims, con_claims = ag.generate_initial_claims("AI Expansion")
    assert len(pro_claims) == 6
    assert len(con_claims) == 6
    
    args = ag.generate_arguments(Side.PRO, "AI Expansion", pro_claims, con_claims, [], count=2)
    assert len(args) == 2
    assert args[0].strength > 0.0

@pytest.mark.asyncio
async def test_debate_service_run_debate():
    service = DebateService(max_rounds=1, seed=42)
    # mock facts provider
    async def mock_facts_provider(topic):
        return (["Pro statement 1"], ["Con statement 1"])
        
    result = await service.run_debate(
        topic="Testing",
        rounds=1,
        facts_provider=mock_facts_provider,
        persona=Persona.DEFAULT
    )
    
    assert result.state.topic == "Testing"
    assert len(result.state.history) == 8  # 4 rounds (min bound) = 8 moves
    assert result.facts_from_api is True
    
    summary = service.summarize(result.state)
    assert "winner" in summary
    assert "final_belief" in summary
