from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from app.config import get_settings
from app.deps import UserContext
from app.ai_orchestrator.models import AIRun, AIRunInput, TaskTypeEnum
from app.ai_orchestrator.schemas import CreateAIRunRequest
from app.ai_orchestrator.workflows.debate_workflow import DebateWorkflow


class AIOrchestratorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_run(self, payload: CreateAIRunRequest, user: UserContext) -> AIRun:
        run = AIRun(
            org_id=user.org_id,
            project_id=payload.project_id,
            task_type=TaskTypeEnum(payload.task_type),
            repo_commit=payload.repo_commit,
            base_branch=payload.base_branch,
            working_branch=payload.working_branch,
            requested_by=user.user_id,
        )
        self.db.add(run)
        await self.db.flush()

        run_input = AIRunInput(
            run_id=run.id,
            scope_json=payload.scope,
            constraints_json=payload.constraints,
            acceptance_criteria_json=payload.acceptance_criteria,
        )
        self.db.add(run_input)
        await self.db.commit()
        await self.db.refresh(run)

        settings = get_settings()
        
        try:
            client = await Client.connect(settings.temporal_server, namespace=settings.temporal_namespace)
            await client.start_workflow(
                DebateWorkflow.run,
                run.id,
                id=f"ai-run-{run.id}",
                task_queue="ai-orchestrator"
            )
        except Exception as e:
            # We log but continue, Temporal might be down in dev
            print(f"Warning: Failed to launch Temporal workflow for AI Run {run.id}: {e}")

        return run
