// ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// ========= Copyright 2025-2026 @ Eigent.ai All Rights Reserved. =========

import {
  confirmRequirements,
  provideRequirements,
  updatePlan,
} from '@/api/workflow';
import type { ChatStore, PlanTask } from '@/store/chatStore';
import { useCallback, useMemo, useState } from 'react';
import { PlanEditor } from './PlanEditor';
import { RequirementsChecklist } from './RequirementsChecklist';
import { WorkflowPhaseIndicator } from './WorkflowPhaseIndicator';

interface WorkflowPanelProps {
  taskId: string;
  chatStore: ChatStore;
  projectId: string;
}

export function WorkflowPanel({
  taskId,
  chatStore,
  projectId,
}: WorkflowPanelProps) {
  const [isValidating, setIsValidating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  const task = chatStore.tasks[taskId];
  const workflowState = task?.workflowState;
  const planDraft = task?.planDraft;
  const analysisProgress = task?.analysisProgress || '';
  const isReadyToStart = task?.isReadyToStart || false;

  const isStep2 = useMemo(() => {
    return (
      workflowState?.phase === 'understanding' &&
      workflowState?.step === 'step2'
    );
  }, [workflowState?.phase, workflowState?.step]);

  const isStep3OrReady = useMemo(() => {
    return (
      (workflowState?.phase === 'understanding' &&
        workflowState?.step === 'step3') ||
      workflowState?.is_ready_to_start
    );
  }, [
    workflowState?.phase,
    workflowState?.step,
    workflowState?.is_ready_to_start,
  ]);

  const handleProvideRequirement = useCallback(
    async (requirementId: string, value: string) => {
      chatStore.updateRequirement(taskId, requirementId, value);
      try {
        await provideRequirements(projectId, [{ id: requirementId, value }]);
      } catch (error) {
        console.error('Failed to provide requirement:', error);
      }
    },
    [chatStore, taskId, projectId]
  );

  const handleValidateAll = useCallback(async () => {
    setIsValidating(true);
    try {
      await confirmRequirements(projectId);
    } catch (error) {
      console.error('Failed to validate requirements:', error);
    } finally {
      setIsValidating(false);
    }
  }, [projectId]);

  const handleAddTask = useCallback(
    async (content: string) => {
      try {
        const newTask: PlanTask = {
          id: `task-${Date.now()}`,
          content,
          dependencies: [],
          tools_needed: [],
          status: 'pending',
        };
        await updatePlan(projectId, {
          update_type: 'add_task',
          task_data: newTask,
        });
      } catch (error) {
        console.error('Failed to add task:', error);
      }
    },
    [projectId]
  );

  const handleRemoveTask = useCallback(
    async (planTaskId: string) => {
      try {
        await updatePlan(projectId, {
          update_type: 'remove_task',
          task_id: planTaskId,
        });
      } catch (error) {
        console.error('Failed to remove task:', error);
      }
    },
    [projectId]
  );

  const handleModifyTask = useCallback(
    async (planTaskId: string, content: string) => {
      chatStore.updatePlanTask(taskId, planTaskId, { content });
      try {
        await updatePlan(projectId, {
          update_type: 'modify_task',
          task_id: planTaskId,
          task_data: { content } as PlanTask,
        });
      } catch (error) {
        console.error('Failed to modify task:', error);
      }
    },
    [chatStore, taskId, projectId]
  );

  const handleReorderTasks = useCallback(
    async (taskOrder: string[]) => {
      try {
        await updatePlan(projectId, {
          update_type: 'reorder_tasks',
          task_order: taskOrder,
        });
      } catch (error) {
        console.error('Failed to reorder tasks:', error);
      }
    },
    [projectId]
  );

  const handleStartExecution = useCallback(async () => {
    setIsExecuting(true);
    try {
      // chatStore.startExecution now handles both local state update AND API call
      await chatStore.startExecution(taskId);
    } catch (error) {
      console.error('Failed to start execution:', error);
    } finally {
      setIsExecuting(false);
    }
  }, [chatStore, taskId]);

  if (!workflowState) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3">
      <WorkflowPhaseIndicator
        workflowState={workflowState}
        analysisProgress={analysisProgress}
      />

      {isStep2 && workflowState.requirements.length > 0 && (
        <RequirementsChecklist
          requirements={workflowState.requirements}
          onProvideRequirement={handleProvideRequirement}
          onValidateAll={handleValidateAll}
          isValidating={isValidating}
        />
      )}

      {isStep3OrReady && planDraft && (
        <PlanEditor
          planDraft={planDraft}
          isReadyToStart={isReadyToStart}
          onAddTask={handleAddTask}
          onRemoveTask={handleRemoveTask}
          onModifyTask={handleModifyTask}
          onReorderTasks={handleReorderTasks}
          onStartExecution={handleStartExecution}
          disabled={isExecuting}
        />
      )}
    </div>
  );
}
