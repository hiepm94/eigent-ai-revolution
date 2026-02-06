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

import { WorkflowState } from '@/store/chatStore';
import { Brain, Check, ClipboardCheck, ListTodo, Play } from 'lucide-react';
import { useMemo } from 'react';

interface WorkflowPhaseIndicatorProps {
  workflowState: WorkflowState | null;
  analysisProgress: string;
}

interface StepConfig {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const understandingSteps: StepConfig[] = [
  { id: 'step1', label: 'Analyzing', icon: <Brain size={16} /> },
  { id: 'step2', label: 'Collecting', icon: <ClipboardCheck size={16} /> },
  { id: 'step3', label: 'Planning', icon: <ListTodo size={16} /> },
];

export function WorkflowPhaseIndicator({
  workflowState,
  analysisProgress,
}: WorkflowPhaseIndicatorProps) {
  const currentStepIndex = useMemo(() => {
    if (!workflowState?.step) return -1;
    return understandingSteps.findIndex((s) => s.id === workflowState.step);
  }, [workflowState?.step]);

  const isExecutionPhase = useMemo(() => {
    return (
      workflowState?.phase === 'execution' ||
      workflowState?.phase === 'completed'
    );
  }, [workflowState?.phase]);

  const statusMessage = useMemo(() => {
    return workflowState?.status_message || analysisProgress;
  }, [workflowState?.status_message, analysisProgress]);

  if (!workflowState) {
    return null;
  }

  return (
    <div className="flex w-full flex-col gap-3 rounded-xl border bg-task-surface px-sm py-sm">
      <div className="flex items-center gap-1">
        {understandingSteps.map((step, index) => {
          const isCompleted =
            isExecutionPhase ||
            (workflowState.phase === 'understanding' &&
              index < currentStepIndex);
          const isCurrent =
            workflowState.phase === 'understanding' &&
            index === currentStepIndex;

          return (
            <div key={step.id} className="flex items-center">
              <div
                className={`flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium transition-all duration-300 ${
                  isCompleted
                    ? 'bg-bg-fill-success-primary text-white'
                    : isCurrent
                      ? 'text-white bg-border-primary'
                      : 'bg-task-fill-default text-text-tertiary'
                }`}
              >
                <span className="flex-shrink-0">
                  {isCompleted ? <Check size={14} /> : step.icon}
                </span>
                <span className="whitespace-nowrap">{step.label}</span>
              </div>
              {index < understandingSteps.length - 1 && (
                <div
                  className={`mx-1 h-0.5 w-4 transition-colors duration-300 ${
                    isCompleted
                      ? 'bg-bg-fill-success-primary'
                      : 'bg-border-secondary'
                  }`}
                />
              )}
            </div>
          );
        })}

        <div
          className={`mx-1 h-0.5 w-4 transition-colors duration-300 ${
            isExecutionPhase
              ? 'bg-bg-fill-success-primary'
              : 'bg-border-secondary'
          }`}
        />

        <div
          className={`flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium transition-all duration-300 ${
            workflowState.phase === 'completed'
              ? 'bg-bg-fill-success-primary text-white'
              : isExecutionPhase
                ? 'text-white bg-border-primary'
                : 'bg-task-fill-default text-text-tertiary'
          }`}
        >
          <span className="flex-shrink-0">
            {workflowState.phase === 'completed' ? (
              <Check size={14} />
            ) : (
              <Play size={14} />
            )}
          </span>
          <span className="whitespace-nowrap">Execution</span>
        </div>
      </div>

      {statusMessage && (
        <div className="text-xs font-medium text-text-secondary">
          {statusMessage}
        </div>
      )}
    </div>
  );
}
