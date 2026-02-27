"""Compatibility wrapper for legacy imports."""
try:
    from backend.services.debate_service import DebateService
except ModuleNotFoundError:  # Vercel backend project rooted at /backend
    from services.debate_service import DebateService


class DebateRunner(DebateService):
    """Backward-compatible alias for DebateService."""

    def run(self, topic, initial_pro=None, initial_con=None):
        if initial_pro is not None and initial_con is not None:
            result = self.run_debate(topic, self.max_rounds, facts_provider=lambda _topic: (initial_pro, initial_con))
        else:
            result = self.run_debate(topic, self.max_rounds)
        return result.state, result.pruning_logs
