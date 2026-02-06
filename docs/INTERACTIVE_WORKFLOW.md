# Interactive Workflow System

This document describes the new interactive workflow system that transforms eigent from a direct "message → execute" model to a guided, multi-phase workflow with user interaction.

## Overview

The new system implements a two-phase workflow:

### Phase 1: Understanding & Analysis (3 steps)

1. **Step 1 - Classify & Analyze**: Auto-research without user confirmation
2. **Step 2 - Collect & Validate**: User provides info, agent validates resources
3. **Step 3 - Plan & Edit**: Generate task plan, allow user modifications via chat

### Phase 2: Execution

- Execute tasks with interactive error handling
- Allow modifications based on results
- Output final workflow guide for later execution

### Scheduling Features (Future)

- Detect schedule requests in user messages
- Trigger workflows on schedule after first success
- Notify users before scheduled execution

## Architecture

### Backend Components

#### New Files

- `backend/app/service/workflow.py` - Workflow phase models and enums
- `backend/app/service/workflow_handler.py` - Phase 1 step handlers
- `backend/app/agent/workflow_orchestrator.py` - Request classification, requirements analysis

#### Modified Files

- `backend/app/service/task.py` - New Action types for workflow events
- `backend/app/service/chat_service.py` - Integrated workflow flow with feature flag
- `backend/app/controller/chat_controller.py` - New API endpoints

#### New API Endpoints

- `POST /chat/{id}/provide-requirements` - User provides requirement values
- `POST /chat/{id}/confirm-requirements` - Proceed to plan generation
- `POST /chat/{id}/update-plan` - Modify task plan
- `POST /chat/{id}/start-execution` - Start actual execution
- `GET /chat/{id}/workflow-state` - Get current workflow state
- `GET /chat/{id}/plan-draft` - Get current plan draft

### Frontend Components

#### New Files

- `src/api/workflow.ts` - API functions for workflow endpoints
- `src/components/ChatBox/WorkflowPhase/WorkflowPhaseIndicator.tsx` - Phase stepper
- `src/components/ChatBox/WorkflowPhase/RequirementsChecklist.tsx` - Requirements UI
- `src/components/ChatBox/WorkflowPhase/PlanEditor.tsx` - Plan editing UI
- `src/components/ChatBox/WorkflowPhase/WorkflowPanel.tsx` - Container panel
- `src/components/ChatBox/MessageItem/PlanDraftCard.tsx` - Plan message card

#### Modified Files

- `src/types/constants.ts` - New AgentStep and ChatTaskStatus values
- `src/store/chatStore.ts` - New workflow state fields and methods
- `src/components/ChatBox/index.tsx` - Updated state handling for planning phases
- `src/components/ChatBox/BottomBox/index.tsx` - New BottomBoxState values
- `src/components/ChatBox/UserQueryGroup.tsx` - Plan draft message rendering

## Configuration

### Feature Flag

The interactive workflow is controlled by a feature flag in `chat_service.py`:

```python
USE_INTERACTIVE_WORKFLOW = True  # Set to False to use original flow
```

## Workflow States

### Backend Enums

```python
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
```

### Frontend Status Values

```typescript
ChatTaskStatus = {
  // ... existing values
  ANALYZING: 'analyzing', // Phase 1 Step 1
  COLLECTING: 'collecting', // Phase 1 Step 2
  PLANNING: 'planning', // Phase 1 Step 3
  READY: 'ready', // Ready to start execution
};
```

## SSE Events

### New Events (Backend → Frontend)

- `workflow_state` - Current phase/step status
- `analyzing` - Analysis progress updates
- `requirements` - List of detected requirements
- `requirements_validation` - Validation results
- `requirements_ready` - All requirements validated
- `plan_draft` - Task plan for editing
- `schedule_suggestion` - Detected schedule patterns

### New Actions (Frontend → Backend)

- `provide_requirements` - User provides requirement values
- `confirm_requirements` - User confirms to proceed
- `update_plan` - User modifies task plan
- `start_execution` - User clicks Start Task

## User Flow

1. User sends message
2. Agent classifies request (simple/complex/scheduled)
3. If simple: answer directly and wait for follow-up
4. If complex/scheduled:
   a. Analyze requirements (MCP servers, API keys, files, etc.)
   b. Show prerequisites checklist to user
   c. User provides missing info
   d. Agent validates all requirements
   e. Generate task plan and show to user
   f. User can modify plan via chat
   g. User clicks "Start Task"
   h. Execute tasks with interactive error handling

## Memory Organization

### Context Packs

- `workflow_state` - Current phase/step data
- `plan_draft` - Editable task plan
- `original_message` - User's original request
- `requirements` - Collected requirements with values

All stored in TaskLock for persistence across SSE events.
