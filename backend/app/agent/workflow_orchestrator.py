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
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

from camel.agents import ChatAgent
from camel.models import ModelFactory

from app.service.workflow import (
    RequestType,
    RequirementItem,
    RequirementStatus,
    RequirementType,
    ScheduleSuggestion,
)

logger = logging.getLogger("workflow_orchestrator")

SCHEDULE_PATTERNS = {
    r"every\s+day\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?": "daily",
    r"daily\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?": "daily",
    r"every\s+morning": "daily_morning",
    r"every\s+evening": "daily_evening",
    r"nightly": "nightly",
    r"weekly\s+on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)": "weekly",
    r"every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)": "weekly",
    r"in\s+(\d+)\s+hours?": "delay_hours",
    r"in\s+(\d+)\s+minutes?": "delay_minutes",
    r"every\s+(\d+)\s+hours?": "recurring_hours",
    r"every\s+(\d+)\s+minutes?": "recurring_minutes",
    r"hourly": "hourly",
}

DAY_TO_CRON = {
    "sunday": "0",
    "monday": "1",
    "tuesday": "2",
    "wednesday": "3",
    "thursday": "4",
    "friday": "5",
    "saturday": "6",
}

CLASSIFICATION_PROMPT = """You are a request classifier. Analyze the user's message and classify it into one of these categories:

1. SIMPLE_ANSWER - The request can be answered directly without executing any agents or tools. Examples:
   - "What is Python?"
   - "How do I create a list in JavaScript?"
   - "Explain REST APIs"

2. AGENT_TASK - The request requires agent execution (browser automation, code development, file operations, etc.). Examples:
   - "Go to google.com and search for weather"
   - "Create a Python script that calculates factorial"
   - "Download the file from this URL"
   - "Build a React component for a login form"

3. SCHEDULED_TASK - The request contains scheduling triggers AND requires agent execution. Examples:
   - "Every day at 9am, check my email"
   - "Weekly on Monday, run the backup script"
   - "In 2 hours, send me a reminder"

User message: {message}

Respond with ONLY one of: SIMPLE_ANSWER, AGENT_TASK, or SCHEDULED_TASK"""

REQUIREMENTS_PROMPT = """You are a requirements analyzer. 

## Here are Types & Skills You Have To Complete User's Task:
(This is provided tool/ resource that you can use to help complete the user's request, besides tools/ resources the user may provide)
1. **Developer Agent** - Lead Software Engineer
   - Unrestricted code execution (any language)
   - Full terminal/shell access
   - GUI automation (AppleScript on macOS, pyautogui on other OS)
   - Screen observation and desktop automation
   - Can schedule tasks using cron expressions and one-time delays

2. **Browser Agent** - Senior Research Analyst
   - Web search and research
   - Browser automation and navigation
   - Page interaction and form filling
   - Data extraction from websites
   - Note-taking and information documentation

3. **Document Agent** - Documentation Specialist
   - Create/modify documents (text, office, presentations, spreadsheets)
   - HTML generation
   - File system operations
   - Data processing and formatting
   - Can schedule document generation tasks

4. **Multi-Modal Agent** - Creative Content Specialist
   - Video and audio analysis
   - Image analysis and understanding
   - Image generation (DALL-E)
   - Media format conversion
   - Transcription services

## Task Scheduling
- **Recurring patterns**: Cron expressions (daily, weekly, hourly, custom intervals)
- **One-time execution**: Delayed execution (in X hours/minutes)
- Examples: "every day at 9am", "weekly on Monday", "in 2 hours", "every 30 minutes"
Known you will schedule on your own so user don't have to provide things like automation tools.
---
Analyze the user's message and identify what resources, tools, or access are needed to complete the task.
For each requirement, determine:
- type: One of [mcp_server, api_key, file_access, browser, terminal, tool, other]
- name: Short identifier for the requirement
- description: What this requirement is for
- required: Whether it's essential (true) or optional (false)
- reason: Why this is needed
- how_to_provide: Instructions for the user on how to provide this

User message: {message}

Respond in this JSON format:
{{
  "requirements": [
    {{
      "type": "browser",
      "name": "browser_access",
      "description": "Web browser for navigation",
      "required": true,
      "reason": "Need to visit websites and interact with web pages",
      "how_to_provide": "Ensure browser automation is enabled in settings"
    }}
  ]
}}

If no special requirements are needed, return: {{"requirements": []}}"""

SCHEDULE_DETECTION_PROMPT = """You are a schedule parser. Analyze the user's message to detect any scheduling patterns.

Look for patterns like:
- "every day at 9am" → cron: "0 9 * * *"
- "weekly on Monday" → cron: "0 0 * * 1"
- "in 2 hours" → one-time delayed execution
- "nightly" → cron: "0 0 * * *"
- "every 30 minutes" → cron: "*/30 * * * *"
- "hourly" → cron: "0 * * * *"

User message: {message}

Respond in this JSON format:
{{
  "detected": true/false,
  "cron": "cron expression if recurring, null otherwise",
  "run_at": "ISO datetime string if one-time delay, null otherwise",
  "is_recurring": true/false,
  "description": "Human-readable description of the schedule",
  "timezone": "UTC"
}}

If no schedule is detected, return: {{"detected": false}}"""

PREREQUISITES_RESPONSE_PROMPT = """You are a helpful assistant preparing a response about task prerequisites.

The user wants to perform a task. Based on the analysis, generate a friendly, clear response that:
1. Summarizes what the task will do
2. Lists any requirements/prerequisites needed
3. If there's a schedule, explain when it will run
4. Provides a checklist of what the user needs to confirm/provide

User's original message: {message}

Requirements found:
{requirements}

Schedule detected:
{schedule}

Generate a clear, structured response for the user.
If there are no schedule, doesn't need to mention it."""


def _create_agent(model_config: Any) -> ChatAgent:
    """Create a ChatAgent for LLM calls using the provided model configuration."""
    model = ModelFactory.create(
        model_platform=model_config.model_platform,
        model_type=model_config.model_type,
        api_key=model_config.api_key,
        url=getattr(model_config, "api_url", None),
        timeout=120,
    )
    return ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        step_timeout=300,
    )


async def classify_request(message: str, model_config: Any) -> RequestType:
    """Classify user request type using LLM.

    Args:
        message: The user's input message
        model_config: Model configuration with platform, type, api_key, etc.

    Returns:
        RequestType enum indicating the classification
    """
    agent = _create_agent(model_config)
    prompt = CLASSIFICATION_PROMPT.format(message=message)

    try:
        response = await agent.astep(prompt)
        result = response.msg.content.strip().upper()

        if "SIMPLE_ANSWER" in result:
            return RequestType.SIMPLE_ANSWER
        elif "SCHEDULED_TASK" in result:
            return RequestType.SCHEDULED_TASK
        elif "AGENT_TASK" in result:
            return RequestType.AGENT_TASK
        else:
            logger.warning(
                f"Unexpected classification result: {result}, defaulting to AGENT_TASK"
            )
            return RequestType.AGENT_TASK
    except Exception as e:
        logger.error(f"Error classifying request: {e}", exc_info=True)
        return RequestType.AGENT_TASK


async def analyze_requirements(
    message: str, model_config: Any
) -> list[RequirementItem]:
    """Analyze and extract requirements from user message.

    Args:
        message: The user's input message
        model_config: Model configuration with platform, type, api_key, etc.

    Returns:
        List of RequirementItem objects
    """
    agent = _create_agent(model_config)
    prompt = REQUIREMENTS_PROMPT.format(message=message)

    try:
        response = await agent.astep(prompt)
        content = response.msg.content.strip()

        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            logger.warning("No JSON found in requirements response")
            return []

        import json

        data = json.loads(json_match.group())
        requirements = []

        for req in data.get("requirements", []):
            try:
                req_type = RequirementType(req.get("type", "other"))
            except ValueError:
                req_type = RequirementType.OTHER

            requirement = RequirementItem(
                id=str(uuid.uuid4()),
                type=req_type,
                name=req.get("name", "unknown"),
                description=req.get("description", ""),
                required=req.get("required", True),
                reason=req.get("reason"),
                how_to_provide=req.get("how_to_provide"),
                status=RequirementStatus.MISSING,
            )
            requirements.append(requirement)

        return requirements
    except Exception as e:
        logger.error(f"Error analyzing requirements: {e}", exc_info=True)
        return []


def _parse_time_to_hour(
    hour_str: str, minute_str: str | None, ampm: str | None
) -> tuple[int, int]:
    """Parse time components to 24-hour format."""
    hour = int(hour_str)
    minute = int(minute_str) if minute_str else 0

    if ampm:
        ampm = ampm.lower()
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

    return hour, minute


def _parse_schedule_pattern(message: str) -> ScheduleSuggestion | None:
    """Parse schedule patterns from message using regex."""
    message_lower = message.lower()

    for pattern, schedule_type in SCHEDULE_PATTERNS.items():
        match = re.search(pattern, message_lower)
        if match:
            if schedule_type == "daily":
                hour, minute = _parse_time_to_hour(
                    match.group(1),
                    match.group(2) if match.lastindex >= 2 else None,
                    match.group(3) if match.lastindex >= 3 else None,
                )
                return ScheduleSuggestion(
                    detected=True,
                    cron=f"{minute} {hour} * * *",
                    is_recurring=True,
                    description=f"Daily at {hour:02d}:{minute:02d}",
                    timezone="UTC",
                )
            elif schedule_type == "daily_morning":
                return ScheduleSuggestion(
                    detected=True,
                    cron="0 9 * * *",
                    is_recurring=True,
                    description="Every morning at 9:00 AM",
                    timezone="UTC",
                )
            elif schedule_type == "daily_evening":
                return ScheduleSuggestion(
                    detected=True,
                    cron="0 18 * * *",
                    is_recurring=True,
                    description="Every evening at 6:00 PM",
                    timezone="UTC",
                )
            elif schedule_type == "nightly":
                return ScheduleSuggestion(
                    detected=True,
                    cron="0 0 * * *",
                    is_recurring=True,
                    description="Nightly at midnight",
                    timezone="UTC",
                )
            elif schedule_type == "weekly":
                day = match.group(1).lower()
                day_num = DAY_TO_CRON.get(day, "1")
                return ScheduleSuggestion(
                    detected=True,
                    cron=f"0 0 * * {day_num}",
                    is_recurring=True,
                    description=f"Weekly on {day.capitalize()}",
                    timezone="UTC",
                )
            elif schedule_type == "delay_hours":
                hours = int(match.group(1))
                run_at = datetime.now() + timedelta(hours=hours)
                return ScheduleSuggestion(
                    detected=True,
                    run_at=run_at,
                    is_recurring=False,
                    description=f"In {hours} hour(s)",
                    timezone="UTC",
                )
            elif schedule_type == "delay_minutes":
                minutes = int(match.group(1))
                run_at = datetime.now() + timedelta(minutes=minutes)
                return ScheduleSuggestion(
                    detected=True,
                    run_at=run_at,
                    is_recurring=False,
                    description=f"In {minutes} minute(s)",
                    timezone="UTC",
                )
            elif schedule_type == "recurring_hours":
                hours = int(match.group(1))
                return ScheduleSuggestion(
                    detected=True,
                    cron=f"0 */{hours} * * *",
                    is_recurring=True,
                    description=f"Every {hours} hour(s)",
                    timezone="UTC",
                )
            elif schedule_type == "recurring_minutes":
                minutes = int(match.group(1))
                return ScheduleSuggestion(
                    detected=True,
                    cron=f"*/{minutes} * * * *",
                    is_recurring=True,
                    description=f"Every {minutes} minute(s)",
                    timezone="UTC",
                )
            elif schedule_type == "hourly":
                return ScheduleSuggestion(
                    detected=True,
                    cron="0 * * * *",
                    is_recurring=True,
                    description="Every hour",
                    timezone="UTC",
                )

    return None


async def detect_schedule(
    message: str, model_config: Any
) -> ScheduleSuggestion | None:
    """Detect and parse schedule patterns from user message.

    First attempts regex-based parsing, then falls back to LLM if needed.

    Args:
        message: The user's input message
        model_config: Model configuration with platform, type, api_key, etc.

    Returns:
        ScheduleSuggestion if a schedule is detected, None otherwise
    """
    pattern_result = _parse_schedule_pattern(message)
    if pattern_result:
        return pattern_result

    agent = _create_agent(model_config)
    prompt = SCHEDULE_DETECTION_PROMPT.format(message=message)

    try:
        response = await agent.astep(prompt)
        content = response.msg.content.strip()

        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            return None

        import json

        data = json.loads(json_match.group())

        if not data.get("detected", False):
            return None

        run_at = None
        if data.get("run_at"):
            try:
                run_at = datetime.fromisoformat(
                    data["run_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return ScheduleSuggestion(
            detected=True,
            cron=data.get("cron"),
            run_at=run_at,
            is_recurring=data.get("is_recurring", False),
            description=data.get("description"),
            timezone=data.get("timezone", "UTC"),
        )
    except Exception as e:
        logger.error(f"Error detecting schedule: {e}", exc_info=True)
        return None


async def generate_prerequisites_response(
    message: str,
    requirements: list[RequirementItem],
    schedule: ScheduleSuggestion | None,
    model_config: Any,
) -> str:
    """Generate user-friendly response about prerequisites, checklist, etc.

    Args:
        message: The user's original message
        requirements: List of analyzed requirements
        schedule: Detected schedule suggestion
        model_config: Model configuration

    Returns:
        A formatted string response for the user
    """
    req_text = (
        "None"
        if not requirements
        else "\n".join(
            f"- [{req.type.value}] {req.name}: {req.description} (Required: {req.required})"
            for req in requirements
        )
    )

    schedule_text = (
        "None"
        if not schedule or not schedule.detected
        else (
            f"Schedule: {schedule.description}\n"
            f"Cron: {schedule.cron or 'N/A'}\n"
            f"Run at: {schedule.run_at or 'N/A'}\n"
            f"Recurring: {schedule.is_recurring}"
        )
    )

    agent = _create_agent(model_config)
    prompt = PREREQUISITES_RESPONSE_PROMPT.format(
        message=message,
        requirements=req_text,
        schedule=schedule_text,
    )

    try:
        response = await agent.astep(prompt)
        return response.msg.content.strip()
    except Exception as e:
        logger.error(
            f"Error generating prerequisites response: {e}", exc_info=True
        )
        parts = ["## Task Analysis\n"]
        parts.append(f"**Your request:** {message}\n")

        if requirements:
            parts.append("\n### Requirements\n")
            for req in requirements:
                status_icon = (
                    "✅" if req.status == RequirementStatus.VALIDATED else "⬜"
                )
                parts.append(
                    f"{status_icon} **{req.name}** ({req.type.value})"
                )
                parts.append(f"   - {req.description}")
                if req.how_to_provide:
                    parts.append(f"   - How to provide: {req.how_to_provide}")

        if schedule and schedule.detected:
            parts.append("\n### Schedule\n")
            parts.append(f"- {schedule.description}")
            if schedule.cron:
                parts.append(f"- Cron expression: `{schedule.cron}`")

        return "\n".join(parts)


async def validate_requirement(
    requirement: RequirementItem,
) -> RequirementItem:
    """Validate a single requirement (check if MCP installed, API key exists, file accessible).

    Args:
        requirement: The requirement to validate

    Returns:
        Updated RequirementItem with validation status
    """
    import os
    from pathlib import Path

    try:
        if requirement.type == RequirementType.API_KEY:
            env_var_name = (
                requirement.name.upper().replace(" ", "_").replace("-", "_")
            )
            if os.environ.get(env_var_name) or os.environ.get(
                f"{env_var_name}_KEY"
            ):
                requirement.status = RequirementStatus.VALIDATED
            else:
                requirement.status = RequirementStatus.MISSING
                requirement.validation_error = (
                    f"Environment variable {env_var_name} not found"
                )

        elif requirement.type == RequirementType.FILE_ACCESS:
            if requirement.value:
                path = Path(requirement.value)
                if path.exists():
                    requirement.status = RequirementStatus.VALIDATED
                else:
                    requirement.status = RequirementStatus.FAILED
                    requirement.validation_error = (
                        f"Path does not exist: {requirement.value}"
                    )
            else:
                requirement.status = RequirementStatus.MISSING
                requirement.validation_error = "No file path specified"

        elif requirement.type == RequirementType.BROWSER:
            requirement.status = RequirementStatus.VALIDATED

        elif requirement.type == RequirementType.TERMINAL:
            requirement.status = RequirementStatus.VALIDATED

        elif requirement.type == RequirementType.MCP_SERVER:
            requirement.status = RequirementStatus.MISSING
            requirement.validation_error = "MCP server validation requires checking installed_mcp configuration"

        else:
            requirement.status = RequirementStatus.PROVIDED

    except Exception as e:
        requirement.status = RequirementStatus.FAILED
        requirement.validation_error = str(e)
        logger.error(
            f"Error validating requirement {requirement.name}: {e}",
            exc_info=True,
        )

    return requirement


async def validate_all_requirements(
    requirements: list[RequirementItem],
) -> list[RequirementItem]:
    """Validate all requirements and return updated list with validation results.

    Args:
        requirements: List of requirements to validate

    Returns:
        Updated list of RequirementItems with validation statuses
    """
    import asyncio

    validated = await asyncio.gather(
        *[validate_requirement(req) for req in requirements]
    )
    return list(validated)
