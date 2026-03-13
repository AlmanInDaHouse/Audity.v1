from app.ai_orchestrator.schemas import ClaudeOutput, ClaudeFinding, ClaudeImplementationStep

class ClaudeAdapter:
    async def review(self, system_prompt: str, user_prompt: str) -> ClaudeOutput:
        """
        Fake Adapter returning static JSON for testing.
        """
        return ClaudeOutput(
            summary="Se detectó login mock en producción",
            findings=[
                ClaudeFinding(
                    id="F01",
                    severity="high",
                    area="auth",
                    evidence=["app/main.py:140-150"],
                    problem="mock login enabled in production",
                    recommended_fix="disable in non-dev and implement real auth gate"
                )
            ],
            implementation_plan=[
                ClaudeImplementationStep(
                    step=1,
                    action="disable mock login",
                    files=["app/main.py"],
                    risk="low"
                )
            ],
            allowed_scope=["app/main.py", "app/config.py"],
            confidence=0.88
        )
