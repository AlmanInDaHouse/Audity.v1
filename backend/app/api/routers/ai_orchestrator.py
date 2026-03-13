from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from sqlalchemy import select

from app.db import get_db
from app.deps import UserContext, get_current_user
from app.ai_orchestrator.models import AIRun, AIAgentOutput, AIPatchCandidate, AIGuardrailResult, AIDecision
from app.ai_orchestrator.schemas import CreateAIRunRequest
from app.ai_orchestrator.service import AIOrchestratorService

router = APIRouter(prefix="/ai-orchestrator", tags=["AI Orchestrator"])

@router.post("/runs", response_model=dict[str, Any])
async def create_ai_run(
    payload: CreateAIRunRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user)
) -> dict[str, Any]:
    service = AIOrchestratorService(db)
    run = await service.create_run(payload, user)
    return {"run_id": run.id, "status": run.status.value}

@router.get("/runs/{run_id}", response_model=dict[str, Any])
async def get_ai_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user)
) -> dict[str, Any]:
    run = await db.get(AIRun, run_id)
    if not run or run.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Run not found")

    outputs = (await db.execute(select(AIAgentOutput).where(AIAgentOutput.run_id == run_id))).scalars().all()
    patch = await db.scalar(select(AIPatchCandidate).where(AIPatchCandidate.run_id == run_id))
    decision = await db.scalar(select(AIDecision).where(AIDecision.run_id == run_id))
    guardrails = await db.scalar(select(AIGuardrailResult).where(AIGuardrailResult.run_id == run_id))

    return {
        "id": run.id,
        "status": run.status.value,
        "task_type": run.task_type.value,
        "created_at": run.created_at.isoformat(),
        "agents": [{"agent": o.agent_name.value, "round": o.round_number} for o in outputs],
        "patch_proposed": bool(patch),
        "decision": decision.decision.value if decision else None,
        "guardrails_passed": guardrails.lint_passed and guardrails.tests_passed if guardrails else None,
    }
