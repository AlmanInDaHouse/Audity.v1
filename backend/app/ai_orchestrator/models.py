from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import uuid_str, utc_now


class TaskTypeEnum(str, enum.Enum):
    audit_fix = 'audit_fix'
    release_gate = 'release_gate'
    hardening_task = 'hardening_task'


class RunStatusEnum(str, enum.Enum):
    requested = 'requested'
    repo_snapshot_ready = 'repo_snapshot_ready'
    claude_review_done = 'claude_review_done'
    codex_patch_done = 'codex_patch_done'
    gemini_decision_done = 'gemini_decision_done'
    executor_validation_done = 'executor_validation_done'
    approved = 'approved'
    rejected = 'rejected'
    needs_second_round = 'needs_second_round'
    failed = 'failed'


class AgentNameEnum(str, enum.Enum):
    claude = 'claude'
    codex = 'codex'
    gemini = 'gemini'
    executor = 'executor'


class DecisionEnum(str, enum.Enum):
    accept_claude = 'accept_claude'
    accept_codex = 'accept_codex'
    merge = 'merge'
    second_round = 'second_round'


class AIRun(Base):
    __tablename__ = 'ai_runs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    task_type: Mapped[TaskTypeEnum] = mapped_column(Enum(TaskTypeEnum), nullable=False)
    status: Mapped[RunStatusEnum] = mapped_column(Enum(RunStatusEnum), default=RunStatusEnum.requested, index=True)
    repo_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    working_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AIRunInput(Base):
    __tablename__ = 'ai_run_inputs'

    run_id: Mapped[str] = mapped_column(String(36), ForeignKey('ai_runs.id', ondelete='CASCADE'), primary_key=True)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    constraints_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    acceptance_criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AIAgentOutput(Base):
    __tablename__ = 'ai_agent_outputs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey('ai_runs.id', ondelete='CASCADE'), index=True)
    agent_name: Mapped[AgentNameEnum] = mapped_column(Enum(AgentNameEnum), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_text_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AIPatchCandidate(Base):
    __tablename__ = 'ai_patch_candidates'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey('ai_runs.id', ondelete='CASCADE'), index=True)
    proposed_by: Mapped[AgentNameEnum] = mapped_column(Enum(AgentNameEnum), nullable=False)
    diff_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    commands_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default='proposed')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AIGuardrailResult(Base):
    __tablename__ = 'ai_guardrail_results'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey('ai_runs.id', ondelete='CASCADE'), index=True)
    patch_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('ai_patch_candidates.id', ondelete='CASCADE'), nullable=True)
    lint_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    tests_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    coverage_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    security_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    scope_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AIDecision(Base):
    __tablename__ = 'ai_decisions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey('ai_runs.id', ondelete='CASCADE'), index=True)
    decided_by: Mapped[str] = mapped_column(String(64), nullable=False) # gemini / rule_engine
    decision: Mapped[DecisionEnum] = mapped_column(Enum(DecisionEnum), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    merged_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
