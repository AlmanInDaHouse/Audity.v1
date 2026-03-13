from app.ai_orchestrator.schemas import CodexOutput, CodexPatchStep

class CodexAdapter:
    async def implement(self, system_prompt: str, user_prompt: str) -> CodexOutput:
        """
        Fake Adapter returning static JSON for testing.
        """
        return CodexOutput(
            patch_plan=[
                CodexPatchStep(
                    step=1,
                    change="gate /auth/mock/login behind APP_ENV=dev",
                    files=["app/main.py"]
                )
            ],
            diff_summary="Adds production guard and startup assertion",
            commands_to_run=[
                "pytest tests/auth -q",
                "ruff check app"
            ],
            risk_notes=[
                "Could affect local demo flows if APP_ENV not set"
            ],
            confidence=0.84,
            diff_content="--- a/app/main.py\\n+++ b/app/main.py\\n@@ -143,2 +143,4 @@\\n+    if settings.app_env != 'dev':\\n+        raise HTTPException(403, 'Mock login disabled')\\n"
        )
