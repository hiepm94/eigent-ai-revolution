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

import type { PlanDraft, PlanTask, WorkflowState } from '@/store/chatStore';
import { fetchGet, fetchPost } from './http';

/**
 * Provide requirement values to the backend for validation
 */
export async function provideRequirements(
  projectId: string,
  requirements: Array<{ id: string; value: string }>
): Promise<void> {
  await fetchPost(`/chat/${projectId}/provide-requirements`, { requirements });
}

/**
 * Confirm requirements and proceed to plan generation
 */
export async function confirmRequirements(projectId: string): Promise<void> {
  await fetchPost(`/chat/${projectId}/confirm-requirements`, {});
}

/**
 * Update the task plan
 */
export async function updatePlan(
  projectId: string,
  update: {
    update_type:
      | 'add_task'
      | 'remove_task'
      | 'reorder_tasks'
      | 'modify_task'
      | 'approve'
      | 'reject';
    task_id?: string;
    task_data?: PlanTask;
    task_order?: string[];
    feedback?: string;
  }
): Promise<void> {
  await fetchPost(`/chat/${projectId}/update-plan`, update);
}

/**
 * Start task execution after plan approval
 */
export async function startExecution(projectId: string): Promise<void> {
  await fetchPost(`/chat/${projectId}/start-execution`, {});
}

/**
 * Get current workflow state
 */
export async function getWorkflowState(
  projectId: string
): Promise<WorkflowState | null> {
  try {
    const response = await fetchGet(`/chat/${projectId}/workflow-state`);
    return response.workflow_state || null;
  } catch {
    return null;
  }
}

/**
 * Get current plan draft
 */
export async function getPlanDraft(
  projectId: string
): Promise<PlanDraft | null> {
  try {
    const response = await fetchGet(`/chat/${projectId}/plan-draft`);
    return response.plan_draft || null;
  } catch {
    return null;
  }
}
