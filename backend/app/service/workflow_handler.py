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

import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from app.agent.workflow_orchestrator import (
    analyze_requirements,
    classify_request,
    detect_schedule,
    generate_prerequisites_response,
    validate_all_requirements,
)
from app.model.chat import Chat, sse_json
from app.service.task import Action, TaskLock
from app.service.workflow import (
    PlanDraft,
    PlanTask,
    PlanUpdatePayload,
    PlanUpdateType,
    RequestType,
    RequirementItem,
    RequirementStatus,
    ScheduleSuggestion,
    TaskStatus,
    UnderstandingStep,
    WorkflowPhase,
    WorkflowState,
)

logger = logging.getLogger("workflow_handler")


def store_workflow_state(task_lock: TaskLock, state: WorkflowState) -> None:
    """Store workflow state in TaskLock for persistence across SSE events."""
    if not hasattr(task_lock, "workflow_state"):
        task_lock.workflow_state = None
    task_lock.workflow_state = state
    logger.debug(
        "Workflow state stored",
        extra={
            "task_id": task_lock.id,
            "phase": state.phase.value,
            "step": state.step.value if state.step else None,
        },
    )


def get_workflow_state(task_lock: TaskLock) -> WorkflowState | None:
    """Retrieve workflow state from TaskLock."""
    return getattr(task_lock, "workflow_state", None)


def store_plan_draft(task_lock: TaskLock, plan: PlanDraft) -> None:
    """Store plan draft in TaskLock for persistence."""
    if not hasattr(task_lock, "plan_draft"):
        task_lock.plan_draft = None
    task_lock.plan_draft = plan
    logger.debug(
        "Plan draft stored",
        extra={"task_id": task_lock.id, "task_count": len(plan.tasks)},
    )


def get_plan_draft(task_lock: TaskLock) -> PlanDraft | None:
    """Retrieve plan draft from TaskLock."""
    return getattr(task_lock, "plan_draft", None)


def store_original_message(task_lock: TaskLock, message: str) -> None:
    """Store original user message for later use."""
    if not hasattr(task_lock, "original_message"):
        task_lock.original_message = None
    task_lock.original_message = message


def get_original_message(task_lock: TaskLock) -> str | None:
    """Retrieve original user message."""
    return getattr(task_lock, "original_message", None)


async def handle_phase1_step1(
    task_lock: TaskLock,
    options: Chat,
    message: str,
    model_config: Any,
) -> AsyncGenerator[str, None]:
    """Handle Phase 1 Step 1: Classify request and analyze requirements.

    Args:
        task_lock: The TaskLock for this session
        options: Chat options containing model configuration
        message: User's input message
        model_config: Model configuration for LLM calls

    Yields:
        SSE JSON events for the frontend
    """
    logger.info(
        "Starting Phase 1 Step 1: Classify and Analyze",
        extra={"task_id": task_lock.id, "message_length": len(message)},
    )

    store_original_message(task_lock, message)

    initial_state = WorkflowState(
        phase=WorkflowPhase.UNDERSTANDING,
        step=UnderstandingStep.CLASSIFY_ANALYZE,
        status_message="Analyzing your request...",
    )
    store_workflow_state(task_lock, initial_state)

    yield sse_json(
        Action.workflow_state.value,
        initial_state.model_dump(mode="json"),
    )
    yield sse_json(
        Action.analyzing.value,
        {"status": "in_progress", "message": "Classifying request type..."},
    )

    request_type = await classify_request(message, model_config)
    logger.info(
        "Request classified",
        extra={"task_id": task_lock.id, "request_type": request_type.value},
    )

    if request_type == RequestType.SIMPLE_ANSWER:
        yield sse_json(
            Action.analyzing.value,
            {"status": "complete", "request_type": request_type.value},
        )

        # Generate simple answer using the model
        from camel.agents import ChatAgent
        from camel.models import ModelFactory

        try:
            model = ModelFactory.create(
                model_platform=model_config.model_platform,
                model_type=model_config.model_type,
                api_key=model_config.api_key,
                url=getattr(model_config, "api_url", None),
                timeout=120,
            )
            agent = ChatAgent(
                system_message="You are a helpful assistant. Provide clear, concise answers.",
                model=model,
            )
            response = await agent.astep(message)
            answer_content = (
                response.msg.content
                if response.msg
                else "I couldn't generate a response."
            )

            # Add to conversation history
            task_lock.add_conversation("user", message)
            task_lock.add_conversation("assistant", answer_content)

            # Send wait_confirm event with the answer (same as original simple flow)
            yield sse_json(
                "wait_confirm",
                {"content": answer_content, "question": message},
            )
        except Exception as e:
            logger.error(f"Error generating simple answer: {e}", exc_info=True)
            yield sse_json(
                "wait_confirm",
                {
                    "content": "I encountered an error processing your question.",
                    "question": message,
                },
            )

        final_state = WorkflowState(
            phase=WorkflowPhase.COMPLETED,
            step=None,
            status_message="Simple question answered directly.",
        )
        store_workflow_state(task_lock, final_state)
        yield sse_json(
            Action.workflow_state.value,
            final_state.model_dump(mode="json"),
        )
        return

    yield sse_json(
        Action.analyzing.value,
        {"status": "in_progress", "message": "Analyzing requirements..."},
    )

    requirements = await analyze_requirements(message, model_config)
    logger.info(
        "Requirements analyzed",
        extra={
            "task_id": task_lock.id,
            "requirement_count": len(requirements),
        },
    )

    schedule: ScheduleSuggestion | None = None
    if request_type == RequestType.SCHEDULED_TASK:
        yield sse_json(
            Action.analyzing.value,
            {"status": "in_progress", "message": "Detecting schedule..."},
        )
        schedule = await detect_schedule(message, model_config)
        if schedule and schedule.detected:
            logger.info(
                "Schedule detected",
                extra={
                    "task_id": task_lock.id,
                    "cron": schedule.cron,
                    "is_recurring": schedule.is_recurring,
                },
            )

    yield sse_json(
        Action.analyzing.value,
        {"status": "in_progress", "message": "Generating task summary..."},
    )

    prerequisites_response = await generate_prerequisites_response(
        message, requirements, schedule, model_config
    )

    yield sse_json(
        Action.analyzing.value,
        {"status": "complete", "request_type": request_type.value},
    )

    yield sse_json(
        Action.requirements.value,
        {
            "requirements": [
                req.model_dump(mode="json") for req in requirements
            ]
        },
    )

    if schedule and schedule.detected:
        yield sse_json(
            Action.schedule_suggestion.value,
            schedule.model_dump(mode="json"),
        )

    yield sse_json(
        "message",
        {"content": prerequisites_response, "type": "prerequisites"},
    )

    updated_state = WorkflowState(
        phase=WorkflowPhase.UNDERSTANDING,
        step=UnderstandingStep.COLLECT_VALIDATE,
        status_message="Waiting for user to provide requirements...",
        requirements=requirements,
        schedule_suggestion=schedule,
    )
    store_workflow_state(task_lock, updated_state)

    yield sse_json(
        Action.workflow_state.value,
        updated_state.model_dump(mode="json"),
    )

    logger.info(
        "Transitioned to Step 2: Collect and Validate",
        extra={"task_id": task_lock.id},
    )


async def handle_phase1_step2(
    task_lock: TaskLock,
    options: Chat,
    user_input: dict[str, Any],
    requirements: list[RequirementItem],
) -> AsyncGenerator[str, None]:
    """Handle Phase 1 Step 2: Collect and validate requirements.

    Args:
        task_lock: The TaskLock for this session
        options: Chat options
        user_input: User-provided values for requirements
        requirements: Current list of requirements

    Yields:
        SSE JSON events for the frontend
    """
    logger.info(
        "Starting Phase 1 Step 2: Collect and Validate",
        extra={"task_id": task_lock.id, "input_keys": list(user_input.keys())},
    )

    current_state = get_workflow_state(task_lock)
    if current_state:
        current_state.step = UnderstandingStep.COLLECT_VALIDATE
        current_state.status_message = "Validating requirements..."
        store_workflow_state(task_lock, current_state)

    yield sse_json(
        Action.workflow_state.value,
        current_state.model_dump(mode="json") if current_state else {},
    )
    yield sse_json(
        Action.collecting.value,
        {"status": "in_progress", "message": "Updating requirements..."},
    )

    for req in requirements:
        if req.id in user_input:
            req.value = user_input[req.id]
            req.status = RequirementStatus.PROVIDED
            logger.debug(
                "Requirement updated",
                extra={"task_id": task_lock.id, "requirement_id": req.id},
            )

    yield sse_json(
        Action.collecting.value,
        {"status": "in_progress", "message": "Validating all requirements..."},
    )

    validated_requirements = await validate_all_requirements(requirements)

    validation_results: dict[str, bool] = {}
    failed_requirements: list[RequirementItem] = []

    for req in validated_requirements:
        is_valid = req.status in (
            RequirementStatus.VALIDATED,
            RequirementStatus.PROVIDED,
        )
        validation_results[req.id] = is_valid
        if not is_valid and req.required:
            failed_requirements.append(req)

    yield sse_json(
        Action.requirements_validation.value,
        {
            "results": validation_results,
            "requirements": [
                req.model_dump(mode="json") for req in validated_requirements
            ],
        },
    )

    if failed_requirements:
        error_messages = []
        for req in failed_requirements:
            error_msg = (
                req.validation_error or f"{req.name} is missing or invalid"
            )
            error_messages.append(f"- {req.name}: {error_msg}")

        yield sse_json(
            "message",
            {
                "content": "Some requirements need attention:\n"
                + "\n".join(error_messages),
                "type": "error",
            },
        )

        if current_state:
            current_state.requirements = validated_requirements
            current_state.validation_results = validation_results
            current_state.status_message = "Please fix the failed requirements"
            store_workflow_state(task_lock, current_state)

        yield sse_json(
            Action.workflow_state.value,
            current_state.model_dump(mode="json") if current_state else {},
        )

        logger.info(
            "Validation failed, staying in Step 2",
            extra={
                "task_id": task_lock.id,
                "failed_count": len(failed_requirements),
            },
        )
        return

    yield sse_json(
        Action.collecting.value,
        {"status": "complete", "message": "All requirements validated"},
    )
    yield sse_json(Action.requirements_ready.value, {"ready": True})

    updated_state = WorkflowState(
        phase=WorkflowPhase.UNDERSTANDING,
        step=UnderstandingStep.PLAN_EDIT,
        status_message="Requirements validated. Preparing task plan...",
        requirements=validated_requirements,
        validation_results=validation_results,
        schedule_suggestion=current_state.schedule_suggestion
        if current_state
        else None,
    )
    store_workflow_state(task_lock, updated_state)

    yield sse_json(
        Action.workflow_state.value,
        updated_state.model_dump(mode="json"),
    )

    logger.info(
        "Transitioned to Step 3: Plan and Edit",
        extra={"task_id": task_lock.id},
    )


async def handle_phase1_step3(
    task_lock: TaskLock,
    options: Chat,
    requirements: list[RequirementItem],
    schedule: ScheduleSuggestion | None,
    workforce: Any,
) -> AsyncGenerator[str, None]:
    """Handle Phase 1 Step 3: Generate and present editable task plan.

    Args:
        task_lock: The TaskLock for this session
        options: Chat options
        requirements: Validated requirements
        schedule: Optional schedule suggestion
        workforce: Workforce instance for task decomposition

    Yields:
        SSE JSON events for the frontend
    """
    logger.info(
        "Starting Phase 1 Step 3: Plan and Edit",
        extra={"task_id": task_lock.id},
    )

    current_state = get_workflow_state(task_lock)
    if current_state:
        current_state.step = UnderstandingStep.PLAN_EDIT
        current_state.status_message = "Generating task plan..."
        store_workflow_state(task_lock, current_state)

    yield sse_json(
        Action.workflow_state.value,
        current_state.model_dump(mode="json") if current_state else {},
    )
    yield sse_json(
        Action.planning.value,
        {"status": "in_progress", "message": "Decomposing task into steps..."},
    )

    original_message = get_original_message(task_lock)
    if not original_message:
        original_message = options.question

    from camel.tasks import Task as CamelTask

    decompose_task = CamelTask(
        id=str(uuid.uuid4()),
        content=original_message,
    )

    plan_tasks: list[PlanTask] = []

    try:
        subtasks = await workforce.handle_decompose_append_task(
            decompose_task,
            reset=False,
        )

        for i, subtask in enumerate(subtasks):
            plan_task = PlanTask(
                id=subtask.id,
                content=subtask.content,
                agent_type=getattr(subtask, "agent_type", None),
                dependencies=[],
                estimated_time=None,
                tools_needed=[],
                status=TaskStatus.PENDING,
            )
            if i > 0 and subtasks:
                plan_task.dependencies = [subtasks[i - 1].id]
            plan_tasks.append(plan_task)

        logger.info(
            "Task decomposition complete",
            extra={"task_id": task_lock.id, "subtask_count": len(plan_tasks)},
        )
    except Exception as e:
        logger.error(
            f"Error during task decomposition: {e}",
            extra={"task_id": task_lock.id},
            exc_info=True,
        )
        plan_task = PlanTask(
            id=str(uuid.uuid4()),
            content=original_message,
            status=TaskStatus.PENDING,
        )
        plan_tasks = [plan_task]

    plan_draft = PlanDraft(
        tasks=plan_tasks,
        summary=f"Task plan with {len(plan_tasks)} step(s)",
        total_estimated_time=None,
        can_start=True,
    )
    store_plan_draft(task_lock, plan_draft)

    yield sse_json(
        Action.planning.value,
        {"status": "complete", "message": "Task plan ready for review"},
    )
    yield sse_json(
        Action.plan_draft.value,
        plan_draft.model_dump(mode="json"),
    )

    updated_state = WorkflowState(
        phase=WorkflowPhase.UNDERSTANDING,
        step=UnderstandingStep.PLAN_EDIT,
        status_message="Review and edit your task plan. Click 'Start Task' when ready.",
        requirements=requirements,
        schedule_suggestion=schedule,
        is_ready_to_start=True,
    )
    store_workflow_state(task_lock, updated_state)

    yield sse_json(
        Action.workflow_state.value,
        updated_state.model_dump(mode="json"),
    )

    logger.info(
        "Plan ready, waiting for user to start execution",
        extra={"task_id": task_lock.id, "is_ready_to_start": True},
    )


async def handle_plan_update(
    task_lock: TaskLock,
    update_data: PlanUpdatePayload,
) -> AsyncGenerator[str, None]:
    """Handle user modifications to the task plan.

    Args:
        task_lock: The TaskLock for this session
        update_data: Plan update payload with modification details

    Yields:
        SSE JSON events for the frontend
    """
    logger.info(
        "Handling plan update",
        extra={
            "task_id": task_lock.id,
            "update_type": update_data.update_type.value,
        },
    )

    plan_draft = get_plan_draft(task_lock)
    if not plan_draft:
        plan_draft = PlanDraft(tasks=[], can_start=False)

    if update_data.update_type == PlanUpdateType.ADD_TASK:
        if update_data.task_data:
            plan_draft.tasks.append(update_data.task_data)
            logger.debug(
                "Task added to plan",
                extra={
                    "task_id": task_lock.id,
                    "new_task_id": update_data.task_data.id,
                },
            )

    elif update_data.update_type == PlanUpdateType.REMOVE_TASK:
        if update_data.task_id:
            plan_draft.tasks = [
                t for t in plan_draft.tasks if t.id != update_data.task_id
            ]
            for task in plan_draft.tasks:
                if update_data.task_id in task.dependencies:
                    task.dependencies.remove(update_data.task_id)
            logger.debug(
                "Task removed from plan",
                extra={
                    "task_id": task_lock.id,
                    "removed_task_id": update_data.task_id,
                },
            )

    elif update_data.update_type == PlanUpdateType.REORDER_TASKS:
        if update_data.task_order:
            task_map = {t.id: t for t in plan_draft.tasks}
            reordered_tasks = []
            for task_id in update_data.task_order:
                if task_id in task_map:
                    reordered_tasks.append(task_map[task_id])
            for task in plan_draft.tasks:
                if task.id not in update_data.task_order:
                    reordered_tasks.append(task)
            plan_draft.tasks = reordered_tasks
            logger.debug(
                "Tasks reordered",
                extra={
                    "task_id": task_lock.id,
                    "new_order": update_data.task_order,
                },
            )

    elif update_data.update_type == PlanUpdateType.MODIFY_TASK:
        if update_data.task_id and update_data.task_data:
            for i, task in enumerate(plan_draft.tasks):
                if task.id == update_data.task_id:
                    plan_draft.tasks[i] = update_data.task_data
                    break
            logger.debug(
                "Task modified",
                extra={
                    "task_id": task_lock.id,
                    "modified_task_id": update_data.task_id,
                },
            )

    elif update_data.update_type == PlanUpdateType.APPROVE:
        plan_draft.can_start = True
        logger.info(
            "Plan approved by user",
            extra={"task_id": task_lock.id},
        )

    elif update_data.update_type == PlanUpdateType.REJECT:
        plan_draft.can_start = False
        if update_data.feedback:
            logger.info(
                "Plan rejected with feedback",
                extra={
                    "task_id": task_lock.id,
                    "feedback": update_data.feedback,
                },
            )

    plan_draft.summary = f"Task plan with {len(plan_draft.tasks)} step(s)"
    store_plan_draft(task_lock, plan_draft)

    yield sse_json(
        Action.plan_draft.value,
        plan_draft.model_dump(mode="json"),
    )

    current_state = get_workflow_state(task_lock)
    if current_state:
        current_state.is_ready_to_start = plan_draft.can_start
        store_workflow_state(task_lock, current_state)
        yield sse_json(
            Action.workflow_state.value,
            current_state.model_dump(mode="json"),
        )

    logger.info(
        "Plan update complete",
        extra={
            "task_id": task_lock.id,
            "task_count": len(plan_draft.tasks),
            "can_start": plan_draft.can_start,
        },
    )
