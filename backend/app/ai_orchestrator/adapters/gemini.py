from app.ai_orchestrator.schemas import GeminiDecisionOutput, GeminiConflict

class GeminiAdapter:
    async def arbitrate(self, system_prompt: str, claude_output: dict, codex_output: dict) -> GeminiDecisionOutput:
        """
        Fake Adapter returning static JSON for testing.
        """
        return GeminiDecisionOutput(
            decision="merge",
            winner="hybrid",
            reason="Claude identified broader security risk; Codex patch is implementable",
            merge_plan=[
                "Take Codex patch for endpoint gating",
                "Add Claude recommendation for startup environment assertion"
            ],
            conflicts=[
                GeminiConflict(
                    topic="scope",
                    resolution="extend to startup validation"
                )
            ],
            needs_second_round=False
        )
