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
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RequirementItem } from '@/store/chatStore';
import {
  AlertCircle,
  Check,
  FolderOpen,
  Globe,
  HelpCircle,
  Key,
  Loader2,
  Server,
  Terminal,
  Wrench,
  X,
} from 'lucide-react';
import { useState } from 'react';

interface RequirementsChecklistProps {
  requirements: RequirementItem[];
  onProvideRequirement: (requirementId: string, value: string) => void;
  onValidateAll: () => void;
  isValidating: boolean;
}

const typeIconMap: Record<RequirementItem['type'], React.ReactNode> = {
  mcp_server: <Server size={16} />,
  api_key: <Key size={16} />,
  file_access: <FolderOpen size={16} />,
  browser: <Globe size={16} />,
  terminal: <Terminal size={16} />,
  tool: <Wrench size={16} />,
  other: <HelpCircle size={16} />,
};

function getStatusIndicator(status: RequirementItem['status']) {
  switch (status) {
    case 'missing':
      return (
        <div className="flex items-center gap-1 text-text-cuation">
          <AlertCircle size={14} />
          <span className="text-xs">Missing</span>
        </div>
      );
    case 'provided':
      return (
        <div className="flex items-center gap-1 text-yellow-500">
          <AlertCircle size={14} />
          <span className="text-xs">Pending validation</span>
        </div>
      );
    case 'validated':
      return (
        <div className="flex items-center gap-1 text-text-success">
          <Check size={14} />
          <span className="text-xs">Validated</span>
        </div>
      );
    case 'failed':
      return (
        <div className="flex items-center gap-1 text-text-cuation">
          <X size={14} />
          <span className="text-xs">Failed</span>
        </div>
      );
    default:
      return null;
  }
}

function RequirementRow({
  requirement,
  onProvideValue,
}: {
  requirement: RequirementItem;
  onProvideValue: (value: string) => void;
}) {
  const [inputValue, setInputValue] = useState(requirement.value || '');

  const handleSubmit = () => {
    if (inputValue.trim()) {
      onProvideValue(inputValue.trim());
    }
  };

  return (
    <AccordionItem value={requirement.id} className="border-b-0">
      <AccordionTrigger className="py-2 hover:no-underline">
        <div className="flex flex-1 items-center gap-3">
          <span className="flex-shrink-0 text-icon-primary">
            {typeIconMap[requirement.type]}
          </span>
          <div className="flex flex-1 flex-col items-start gap-0.5">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-text-heading">
                {requirement.name}
              </span>
              {requirement.required && (
                <span className="text-xs text-text-cuation">*</span>
              )}
            </div>
            <span className="text-xs text-text-secondary">
              {requirement.description}
            </span>
          </div>
          <div className="flex-shrink-0">
            {getStatusIndicator(requirement.status)}
          </div>
        </div>
      </AccordionTrigger>
      <AccordionContent className="pb-3 pt-0">
        <div className="ml-7 flex flex-col gap-2">
          {requirement.status === 'failed' && requirement.validation_error && (
            <div className="bg-bg-fill-cuation-secondary flex items-start gap-2 rounded-md p-2 text-xs text-text-cuation">
              <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
              <span>{requirement.validation_error}</span>
            </div>
          )}

          {requirement.how_to_provide && (
            <div className="flex items-start gap-2 text-xs text-text-secondary">
              <HelpCircle size={14} className="mt-0.5 flex-shrink-0" />
              <span>{requirement.how_to_provide}</span>
            </div>
          )}

          {(requirement.status === 'missing' ||
            requirement.status === 'failed') && (
            <div className="flex items-center gap-2">
              <Input
                size="sm"
                placeholder="Enter value..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onEnter={handleSubmit}
                className="flex-1"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={handleSubmit}
                disabled={!inputValue.trim()}
              >
                Provide
              </Button>
            </div>
          )}

          {requirement.status === 'validated' && requirement.value && (
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <Check size={14} className="text-text-success" />
              <span className="font-mono">
                {requirement.type === 'api_key'
                  ? '••••••••' + requirement.value.slice(-4)
                  : requirement.value}
              </span>
            </div>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

export function RequirementsChecklist({
  requirements,
  onProvideRequirement,
  onValidateAll,
  isValidating,
}: RequirementsChecklistProps) {
  const validatedCount = requirements.filter(
    (r) => r.status === 'validated'
  ).length;
  const totalCount = requirements.length;

  if (requirements.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-task-surface px-sm py-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-heading">
            Requirements
          </span>
          <span className="text-xs text-text-secondary">
            {validatedCount} of {totalCount} validated
          </span>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={onValidateAll}
          disabled={isValidating || validatedCount === totalCount}
        >
          {isValidating ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Validating...
            </>
          ) : (
            'Validate All'
          )}
        </Button>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-border-secondary">
        <div
          className="bg-bg-fill-success-primary h-full transition-all duration-300"
          style={{ width: `${(validatedCount / totalCount) * 100}%` }}
        />
      </div>

      <Accordion type="multiple" className="w-full">
        {requirements.map((requirement) => (
          <RequirementRow
            key={requirement.id}
            requirement={requirement}
            onProvideValue={(value) =>
              onProvideRequirement(requirement.id, value)
            }
          />
        ))}
      </Accordion>
    </div>
  );
}
