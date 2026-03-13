from typing import Any, Literal
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# Orchestrator Request / Response
# ---------------------------------------------------------

class CreateAIRunRequest(BaseModel):
    project_id: str = Field(..., description="ID of the project to run against")
    task_type: Literal["audit_fix", "release_gate", "hardening_task"]
    repo_commit: str = Field(..., description="Hash of the commit to audit/fix")
    base_branch: str = Field(default="main")
    working_branch: str | None = None
    scope: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria: dict[str, Any] = Field(default_factory=dict)

# ---------------------------------------------------------
# Claude Response Schemas
# ---------------------------------------------------------

class ClaudeFinding(BaseModel):
    id: str
    severity: str
    area: str
    evidence: list[str]
    problem: str
    recommended_fix: str

class ClaudeImplementationStep(BaseModel):
    step: int
    action: str
    files: list[str]
    risk: str

class ClaudeOutput(BaseModel):
    summary: str
    findings: list[ClaudeFinding]
    implementation_plan: list[ClaudeImplementationStep]
    allowed_scope: list[str]
    confidence: float

# ---------------------------------------------------------
# Codex Response Schemas
# ---------------------------------------------------------

class CodexPatchStep(BaseModel):
    step: int
    change: str
    files: list[str]

class CodexOutput(BaseModel):
    patch_plan: list[CodexPatchStep]
    diff_summary: str
    commands_to_run: list[str]
    risk_notes: list[str]
    confidence: float
    diff_content: str | None = Field(default=None, description="The actual unified diff content if requested")
    
# ---------------------------------------------------------
# Gemini Response Schemas
# ---------------------------------------------------------

class GeminiConflict(BaseModel):
    topic: str
    resolution: str

class GeminiDecisionOutput(BaseModel):
    decision: Literal["accept_claude", "accept_codex", "merge", "second_round"]
    winner: str | None = None
    reason: str
    merge_plan: list[str] = Field(default_factory=list)
    conflicts: list[GeminiConflict] = Field(default_factory=list)
    needs_second_round: bool = False

# ---------------------------------------------------------
# Guardrail Validation Schemas
# ---------------------------------------------------------

class GuardrailValidationResult(BaseModel):
    passed: bool
    lint_passed: bool
    tests_passed: bool
    coverage_passed: bool
    security_passed: bool
    scope_passed: bool
    details: dict[str, Any]
    error_message: str | None = None
