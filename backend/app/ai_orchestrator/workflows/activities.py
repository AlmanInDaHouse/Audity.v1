import json
from pydantic import BaseModel
from temporalio import activity
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.db import SessionLocal
from app.ai_orchestrator.models import AIRun, AIAgentOutput, AIPatchCandidate, AIGuardrailResult, AIDecision, RunStatusEnum, AgentNameEnum

from app.ai_orchestrator.adapters.repo import RepoAdapter
from app.ai_orchestrator.adapters.claude import ClaudeAdapter
from app.ai_orchestrator.adapters.codex import CodexAdapter
from app.ai_orchestrator.adapters.gemini import GeminiAdapter
from app.ai_orchestrator.adapters.executor import ExecutorAdapter
from app.ai_orchestrator.schemas import CodexOutput

async def _update_run_status(run_id: str, status: RunStatusEnum):
    async with SessionLocal() as db:
        run = await db.get(AIRun, run_id)
        if run:
            run.status = status
            await db.commit()

@activity.defn(name="prepare_repo_snapshot")
async def prepare_repo_snapshot(run_id: str) -> dict[str, Any]:
    adapter = RepoAdapter()
    snapshot = await adapter.create_snapshot(run_id)
    await _update_run_status(run_id, RunStatusEnum.repo_snapshot_ready)
    return snapshot

@activity.defn(name="run_claude_auditor")
async def run_claude_auditor(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = payload["run_id"]
    adapter = ClaudeAdapter()
    output = await adapter.review("Eres el auditor/arquitecto...", json.dumps(payload))
    
    async with SessionLocal() as db:
        agent_out = AIAgentOutput(
            run_id=run_id,
            agent_name=AgentNameEnum.claude,
            output_json=output.model_dump()
        )
        db.add(agent_out)
        await db.commit()

    await _update_run_status(run_id, RunStatusEnum.claude_review_done)
    return output.model_dump()

@activity.defn(name="run_codex_implementer")
async def run_codex_implementer(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = payload["snapshot"]["run_id"]
    adapter = CodexAdapter()
    output = await adapter.implement("Eres el implementador...", json.dumps(payload))
    
    async with SessionLocal() as db:
        agent_out = AIAgentOutput(
            run_id=run_id,
            agent_name=AgentNameEnum.codex,
            output_json=output.model_dump()
        )
        db.add(agent_out)
        
        patch_candidate = AIPatchCandidate(
            run_id=run_id,
            proposed_by=AgentNameEnum.codex,
            files_json=[step.files for step in output.patch_plan],
            commands_json=output.commands_to_run,
            risk_level="medium"
        )
        db.add(patch_candidate)
        await db.commit()

    await _update_run_status(run_id, RunStatusEnum.codex_patch_done)
    return output.model_dump()

@activity.defn(name="run_gemini_arbiter")
async def run_gemini_arbiter(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = payload["run_id"]
    adapter = GeminiAdapter()
    output = await adapter.arbitrate("Eres el arbitro...", payload["claude"], payload["codex"])
    
    async with SessionLocal() as db:
        agent_out = AIAgentOutput(
            run_id=run_id,
            agent_name=AgentNameEnum.gemini,
            output_json=output.model_dump()
        )
        db.add(agent_out)
        
        decision = AIDecision(
            run_id=run_id,
            decided_by="gemini",
            decision=output.decision,
            rationale=output.reason,
            merged_plan_json={"plan": output.merge_plan}
        )
        db.add(decision)
        await db.commit()

    await _update_run_status(run_id, RunStatusEnum.gemini_decision_done)
    return output.model_dump()

@activity.defn(name="execute_with_guardrails")
async def execute_with_guardrails(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = payload["snapshot"]["run_id"]
    adapter = ExecutorAdapter()
    scope = payload["claude"].get("allowed_scope", [])
    patch = CodexOutput(**payload["codex"])
    result = await adapter.apply_and_validate(payload["snapshot"], patch, scope)
    
    async with SessionLocal() as db:
        guardrail_res = AIGuardrailResult(
            run_id=run_id,
            lint_passed=result.lint_passed,
            tests_passed=result.tests_passed,
            coverage_passed=result.coverage_passed,
            security_passed=result.security_passed,
            scope_passed=result.scope_passed,
            details_json=result.details
        )
        db.add(guardrail_res)
        await db.commit()

    final_status = RunStatusEnum.approved if result.passed else RunStatusEnum.failed
    await _update_run_status(run_id, final_status)
    return result.model_dump()
