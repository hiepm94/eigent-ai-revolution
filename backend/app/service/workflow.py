# ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class WorkflowPhase(str, Enum):
    UNDERSTANDING = "understanding"
    EXECUTION = "execution"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UnderstandingStep(str, Enum):
    CLASSIFY_ANALYZE = "step1"
    COLLECT_VALIDATE = "step2"
    PLAN_EDIT = "step3"


class RequestType(str, Enum):
    SIMPLE_ANSWER = "simple_answer"
    AGENT_TASK = "agent_task"
    SCHEDULED_TASK = "scheduled_task"


class RequirementStatus(str, Enum):
    MISSING = "missing"
    PROVIDED = "provided"
    VALIDATED = "validated"
    FAILED = "failed"


class RequirementType(str, Enum):
    MCP_SERVER = "mcp_server"
    API_KEY = "api_key"
    FILE_ACCESS = "file_access"
    BROWSER = "browser"
    TERMINAL = "terminal"
    TOOL = "tool"
    OTHER = "other"


class RequirementItem(BaseModel):
    id: str
    type: RequirementType
    name: str
    description: str
    required: bool = True
    reason: str | None = None
    how_to_provide: str | None = None
    status: RequirementStatus = RequirementStatus.MISSING
    value: str | None = None
    validation_error: str | None = None


class ScheduleSuggestion(BaseModel):
    detected: bool = False
    cron: str | None = None
    timezone: str | None = None
    description: str | None = None
    run_at: datetime | None = None
    is_recurring: bool = False


class WorkflowState(BaseModel):
    phase: WorkflowPhase
    step: UnderstandingStep | None = None
    status_message: str | None = None
    requirements: list[RequirementItem] = Field(default_factory=list)
    validation_results: dict[str, bool] = Field(default_factory=dict)
    schedule_suggestion: ScheduleSuggestion | None = None
    is_ready_to_start: bool = False


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanTask(BaseModel):
    id: str
    content: str
    agent_type: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    estimated_time: str | None = None
    tools_needed: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING


class PlanDraft(BaseModel):
    tasks: list[PlanTask] = Field(default_factory=list)
    summary: str | None = None
    total_estimated_time: str | None = None
    can_start: bool = False


class WorkflowGuide(BaseModel):
    title: str
    description: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    verification_checklist: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class ActionWorkflowState(str, Enum):
    workflow_state = "workflow_state"


class ActionPlanDraft(str, Enum):
    plan_draft = "plan_draft"


class ActionScheduleSuggestion(str, Enum):
    schedule_suggestion = "schedule_suggestion"


class ActionUpdatePlan(str, Enum):
    update_plan = "update_plan"


class ActionWorkflowStateData(BaseModel):
    action: Literal[ActionWorkflowState.workflow_state] = (
        ActionWorkflowState.workflow_state
    )
    data: WorkflowState


class ActionPlanDraftData(BaseModel):
    action: Literal[ActionPlanDraft.plan_draft] = ActionPlanDraft.plan_draft
    data: PlanDraft


class ActionScheduleSuggestionData(BaseModel):
    action: Literal[ActionScheduleSuggestion.schedule_suggestion] = (
        ActionScheduleSuggestion.schedule_suggestion
    )
    data: ScheduleSuggestion


class PlanUpdateType(str, Enum):
    ADD_TASK = "add_task"
    REMOVE_TASK = "remove_task"
    REORDER_TASKS = "reorder_tasks"
    MODIFY_TASK = "modify_task"
    APPROVE = "approve"
    REJECT = "reject"


class PlanUpdatePayload(BaseModel):
    update_type: PlanUpdateType
    task_id: str | None = None
    task_data: PlanTask | None = None
    task_order: list[str] | None = None
    feedback: str | None = None


class ActionUpdatePlanData(BaseModel):
    action: Literal[ActionUpdatePlan.update_plan] = (
        ActionUpdatePlan.update_plan
    )
    data: PlanUpdatePayload
