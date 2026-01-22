from typing import Dict, List
from pathlib import Path
from camel.toolkits import MarkItDownToolkit as BaseMarkItDownToolkit

from app.service.task import Agents
from app.utils.listen.toolkit_listen import auto_listen_toolkit
from app.utils.toolkit.abstract_toolkit import AbstractToolkit

# File extensions that should be read as plain text
PLAIN_TEXT_EXTENSIONS = {'.md', '.markdown', '.rst', '.log'}


@auto_listen_toolkit(BaseMarkItDownToolkit)
class MarkItDownToolkit(BaseMarkItDownToolkit, AbstractToolkit):
    agent_name: str = Agents.document_agent

    def __init__(self, api_task_id: str, timeout: float | None = None):
        self.api_task_id = api_task_id
        super().__init__(timeout)

    def read_files(
        self,
        file_paths: List[str],
        message_title: str | None = None,
        message_description: str | None = None,
        message_attachment: str | None = None,
    ) -> Dict[str, str]:
        results: Dict[str, str] = {}
        remaining_files: List[str] = []

        for file_path in file_paths:
            ext = Path(file_path).suffix.lower()
            if ext in PLAIN_TEXT_EXTENSIONS:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        results[file_path] = f.read()
                except Exception as e:
                    results[file_path] = f"Error reading file: {e}"
            else:
                remaining_files.append(file_path)

        if remaining_files:
            base_results = super().read_files(
                remaining_files,
                message_title,
                message_description,
                message_attachment,
            )
            results.update(base_results)

        return results
