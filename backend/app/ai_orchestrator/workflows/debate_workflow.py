from datetime import timedelta
from typing import Any
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.ai_orchestrator.workflows.activities import (
        prepare_repo_snapshot,
        run_claude_auditor,
        run_codex_implementer,
        run_gemini_arbiter,
        execute_with_guardrails
    )

@workflow.defn
class DebateWorkflow:
    @workflow.run
    async def run(self, run_id: str) -> dict[str, Any]:
        snapshot = await workflow.execute_activity(
            prepare_repo_snapshot, run_id, start_to_close_timeout=timedelta(minutes=5)
        )

        claude_output = await workflow.execute_activity(
            run_claude_auditor, {"run_id": run_id, "snapshot": snapshot}, start_to_close_timeout=timedelta(minutes=15)
        )

        codex_output = await workflow.execute_activity(
            run_codex_implementer,
            {"snapshot": snapshot, "claude": claude_output},
            start_to_close_timeout=timedelta(minutes=20)
        )

        gemini_decision = await workflow.execute_activity(
            run_gemini_arbiter,
            {"run_id": run_id, "claude": claude_output, "codex": codex_output},
            start_to_close_timeout=timedelta(minutes=10)
        )

        execution_result = await workflow.execute_activity(
            execute_with_guardrails,
            {
                "snapshot": snapshot,
                "decision": gemini_decision,
                "claude": claude_output,
                "codex": codex_output
            },
            start_to_close_timeout=timedelta(minutes=30)
        )

        return execution_result
