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

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { PlanDraft } from '@/store/chatStore';
import { Clock, Edit3, ListTodo, Play, User } from 'lucide-react';

interface PlanDraftCardProps {
  planDraft: PlanDraft;
  isReadyToStart: boolean;
  onStartTask: () => void;
  onEditPlan: () => void;
  disabled?: boolean;
}

export function PlanDraftCard({
  planDraft,
  isReadyToStart,
  onStartTask,
  onEditPlan,
  disabled = false,
}: PlanDraftCardProps) {
  const { tasks, summary, total_estimated_time, can_start } = planDraft;

  return (
    <div className="bg-white w-full rounded-xl border px-4 py-4">
      <div className="mb-3 flex items-center gap-2">
        <ListTodo className="text-primary h-5 w-5" />
        <span className="text-label-md font-bold">Execution Plan</span>
        {total_estimated_time && (
          <div className="ml-auto flex items-center gap-1 text-xs text-text-body">
            <Clock className="h-3.5 w-3.5" />
            <span>{total_estimated_time}</span>
          </div>
        )}
      </div>

      {summary && <p className="mb-3 text-sm text-text-body">{summary}</p>}

      <div className="mb-4 space-y-2">
        {tasks.map((task, index) => (
          <div
            key={task.id}
            className="flex items-start gap-3 rounded-lg border border-task-border-default bg-message-fill-default p-3"
          >
            <div className="bg-primary text-white flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold">
              {index + 1}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-body">
                {task.content}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {task.agent_type && (
                  <Badge variant="secondary" className="gap-1">
                    <User className="h-3 w-3" />
                    {task.agent_type}
                  </Badge>
                )}
                {task.estimated_time && (
                  <Badge variant="outline" className="gap-1">
                    <Clock className="h-3 w-3" />
                    {task.estimated_time}
                  </Badge>
                )}
                {task.dependencies.length > 0 && (
                  <span className="text-xs text-text-body">
                    Depends on: {task.dependencies.join(', ')}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onEditPlan}
          disabled={disabled}
        >
          <Edit3 className="h-4 w-4" />
          Edit Plan
        </Button>
        {can_start && isReadyToStart && (
          <Button
            variant="primary"
            size="sm"
            onClick={onStartTask}
            disabled={disabled}
          >
            <Play className="h-4 w-4" />
            Start Task
          </Button>
        )}
      </div>
    </div>
  );
}
