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

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PlanDraft, PlanTask } from '@/store/chatStore';
import {
  ChevronDown,
  ChevronUp,
  Edit3,
  GripVertical,
  Play,
  Plus,
  Trash2,
} from 'lucide-react';
import { useState } from 'react';

interface PlanEditorProps {
  planDraft: PlanDraft | null;
  isReadyToStart: boolean;
  onAddTask: (content: string) => void;
  onRemoveTask: (taskId: string) => void;
  onModifyTask: (taskId: string, content: string) => void;
  onReorderTasks: (taskOrder: string[]) => void;
  onStartExecution: () => void;
  disabled?: boolean;
}

interface TaskRowProps {
  task: PlanTask;
  index: number;
  totalTasks: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onModify: (content: string) => void;
  onRemove: () => void;
  disabled?: boolean;
}

function TaskRow({
  task,
  index,
  totalTasks,
  onMoveUp,
  onMoveDown,
  onModify,
  onRemove,
  disabled,
}: TaskRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(task.content);

  const handleSave = () => {
    if (editValue.trim() && editValue !== task.content) {
      onModify(editValue.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(task.content);
    setIsEditing(false);
  };

  return (
    <div className="flex flex-col rounded-lg border bg-bg-primary">
      <div className="flex items-center gap-2 p-2">
        <div className="flex flex-col gap-0.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0"
            onClick={onMoveUp}
            disabled={disabled || index === 0}
          >
            <ChevronUp size={14} />
          </Button>
          <GripVertical size={14} className="mx-auto text-icon-secondary" />
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0"
            onClick={onMoveDown}
            disabled={disabled || index === totalTasks - 1}
          >
            <ChevronDown size={14} />
          </Button>
        </div>

        <div className="flex flex-1 flex-col gap-1">
          {isEditing ? (
            <div className="flex items-center gap-2">
              <Input
                size="sm"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onEnter={handleSave}
                className="flex-1"
                autoFocus
                disabled={disabled}
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={handleSave}
                disabled={disabled || !editValue.trim()}
              >
                Save
              </Button>
              <Button variant="ghost" size="sm" onClick={handleCancel}>
                Cancel
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-text-secondary">
                {index + 1}.
              </span>
              <span className="flex-1 text-sm text-text-heading">
                {task.content}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setIsEditing(true)}
                disabled={disabled}
              >
                <Edit3 size={14} />
              </Button>
            </div>
          )}

          <div className="flex items-center gap-2">
            {task.agent_type && (
              <span className="bg-bg-fill-brand-secondary text-text-brand rounded-full px-2 py-0.5 text-xs">
                {task.agent_type}
              </span>
            )}
            {task.estimated_time && (
              <span className="text-xs text-text-secondary">
                ~{task.estimated_time}
              </span>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs text-text-link hover:underline"
              disabled={disabled}
            >
              {isExpanded ? 'Hide details' : 'Show details'}
            </button>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="hover:bg-bg-fill-cuation-secondary h-7 w-7 p-0 text-text-cuation"
          onClick={onRemove}
          disabled={disabled}
        >
          <Trash2 size={14} />
        </Button>
      </div>

      {isExpanded && (
        <div className="border-t px-3 py-2">
          <div className="flex flex-col gap-2 text-xs">
            {task.dependencies.length > 0 && (
              <div className="flex items-start gap-2">
                <span className="font-medium text-text-secondary">
                  Dependencies:
                </span>
                <span className="text-text-primary">
                  {task.dependencies.join(', ')}
                </span>
              </div>
            )}
            {task.tools_needed.length > 0 && (
              <div className="flex items-start gap-2">
                <span className="font-medium text-text-secondary">
                  Tools needed:
                </span>
                <div className="flex flex-wrap gap-1">
                  {task.tools_needed.map((tool) => (
                    <span
                      key={tool}
                      className="rounded bg-bg-secondary px-1.5 py-0.5 text-text-primary"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {task.dependencies.length === 0 &&
              task.tools_needed.length === 0 && (
                <span className="text-text-secondary">
                  No additional details
                </span>
              )}
          </div>
        </div>
      )}
    </div>
  );
}

export function PlanEditor({
  planDraft,
  isReadyToStart,
  onAddTask,
  onRemoveTask,
  onModifyTask,
  onReorderTasks,
  onStartExecution,
  disabled,
}: PlanEditorProps) {
  const [newTaskContent, setNewTaskContent] = useState('');

  if (!planDraft) {
    return null;
  }

  const handleAddTask = () => {
    if (newTaskContent.trim()) {
      onAddTask(newTaskContent.trim());
      setNewTaskContent('');
    }
  };

  const handleMoveTask = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= planDraft.tasks.length) return;

    const newOrder = [...planDraft.tasks.map((t) => t.id)];
    [newOrder[index], newOrder[newIndex]] = [
      newOrder[newIndex],
      newOrder[index],
    ];
    onReorderTasks(newOrder);
  };

  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-task-surface px-sm py-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text-heading">Task Plan</span>
        <span className="text-xs text-text-secondary">
          {planDraft.tasks.length} task{planDraft.tasks.length !== 1 ? 's' : ''}
          {planDraft.total_estimated_time && (
            <> · ~{planDraft.total_estimated_time}</>
          )}
        </span>
      </div>

      {planDraft.summary && (
        <p className="text-xs text-text-secondary">{planDraft.summary}</p>
      )}

      <div className="flex flex-col gap-2">
        {planDraft.tasks.map((task, index) => (
          <TaskRow
            key={task.id}
            task={task}
            index={index}
            totalTasks={planDraft.tasks.length}
            onMoveUp={() => handleMoveTask(index, 'up')}
            onMoveDown={() => handleMoveTask(index, 'down')}
            onModify={(content) => onModifyTask(task.id, content)}
            onRemove={() => onRemoveTask(task.id)}
            disabled={disabled}
          />
        ))}
      </div>

      <div className="flex items-center gap-2">
        <Input
          size="sm"
          placeholder="Add a new task..."
          value={newTaskContent}
          onChange={(e) => setNewTaskContent(e.target.value)}
          onEnter={handleAddTask}
          className="flex-1"
          disabled={disabled}
        />
        <Button
          variant="secondary"
          size="sm"
          onClick={handleAddTask}
          disabled={disabled || !newTaskContent.trim()}
        >
          <Plus size={14} />
          Add
        </Button>
      </div>

      <div className="flex flex-col gap-2 border-t pt-3">
        <Button
          variant="primary"
          size="md"
          onClick={onStartExecution}
          disabled={disabled || !isReadyToStart}
          className="w-full"
        >
          <Play size={16} />
          Start Task
        </Button>
        <p className="text-center text-xs text-text-secondary">
          💡 You can also modify the plan by chatting with the assistant
        </p>
      </div>
    </div>
  );
}
