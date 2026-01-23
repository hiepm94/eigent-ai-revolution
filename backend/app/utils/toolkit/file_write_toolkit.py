import asyncio
import os
from pathlib import Path
from typing import Dict, List, Union
from camel.toolkits import FileToolkit as BaseFileToolkit
from app.component.environment import env
from app.service.task import process_task
from app.service.task import ActionWriteFileData, Agents, get_task_lock
from app.utils.listen.toolkit_listen import auto_listen_toolkit, listen_toolkit, _safe_put_queue
from app.utils.toolkit.abstract_toolkit import AbstractToolkit

# File extensions that should be read as plain text (not via MarkItDownLoader)
PLAIN_TEXT_EXTENSIONS = {'.md', '.markdown', '.rst', '.log', '.txt'}


@auto_listen_toolkit(BaseFileToolkit)
class FileToolkit(BaseFileToolkit, AbstractToolkit):
    agent_name: str = Agents.document_agent

    def __init__(
        self,
        api_task_id: str,
        working_directory: str | None = None,
        timeout: float | None = None,
        default_encoding: str = "utf-8",
        backup_enabled: bool = True,
    ) -> None:
        if working_directory is None:
            working_directory = env("file_save_path", os.path.expanduser("~/Downloads"))
        super().__init__(working_directory, timeout, default_encoding, backup_enabled)
        self.api_task_id = api_task_id

    @listen_toolkit(
        BaseFileToolkit.write_to_file,
        lambda _,
        title,
        content,
        filename,
        encoding=None,
        use_latex=False: f"write content to file: {filename} with encoding: {encoding} and use_latex: {use_latex}",
    )
    def write_to_file(
        self,
        title: str,
        content: str | List[List[str]],
        filename: str,
        encoding: str | None = None,
        use_latex: bool = False,
    ) -> str:
        res = super().write_to_file(title, content, filename, encoding, use_latex)
        if "Content successfully written to file: " in res:
            task_lock = get_task_lock(self.api_task_id)
            # Capture ContextVar value before creating async task
            current_process_task_id = process_task.get("")

            # Use _safe_put_queue to handle both sync and async contexts
            _safe_put_queue(
                task_lock,
                ActionWriteFileData(
                    process_task_id=current_process_task_id,
                    data=res.replace("Content successfully written to file: ", ""),
                )
            )
        return res

    def _resolve_filepath_for_read(self, file_path: str) -> Path:
        """Resolve filepath for read operations WITHOUT sanitizing the filename.
        
        The base class sanitizes filenames (replacing spaces/special chars with underscores),
        which breaks reading existing files with spaces or non-ASCII characters in their names.
        """
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            path_obj = self.working_directory / path_obj
        return path_obj.resolve()

    def _read_plain_text_file(self, file_path: Path) -> str:
        """Read a file as plain text."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    def read_file(
        self, file_paths: Union[str, List[str]]
    ) -> Union[str, Dict[str, str]]:
        """Read file(s) without sanitizing filenames.
        
        Overrides base class to preserve original filenames with spaces
        and non-ASCII characters (e.g., Vietnamese).
        
        Plain text files (.md, .markdown, .rst, .log, .txt) are read directly
        without using MarkItDownLoader to avoid format support issues.
        """
        from camel.loaders.markitdown import MarkItDownLoader

        try:
            if isinstance(file_paths, str):
                resolved_path = self._resolve_filepath_for_read(file_paths)
                ext = resolved_path.suffix.lower()
                
                if ext in PLAIN_TEXT_EXTENSIONS:
                    return self._read_plain_text_file(resolved_path)
                
                result = MarkItDownLoader().convert_files(
                    file_paths=[str(resolved_path)], parallel=False
                )
                return result.get(
                    str(resolved_path), f"Failed to read file: {resolved_path}"
                )
            else:
                results: Dict[str, str] = {}
                remaining_files: List[str] = []
                remaining_originals: List[str] = []
                
                for fp in file_paths:
                    resolved_path = self._resolve_filepath_for_read(fp)
                    ext = resolved_path.suffix.lower()
                    
                    if ext in PLAIN_TEXT_EXTENSIONS:
                        results[fp] = self._read_plain_text_file(resolved_path)
                    else:
                        remaining_files.append(str(resolved_path))
                        remaining_originals.append(fp)
                
                if remaining_files:
                    markitdown_results = MarkItDownLoader().convert_files(
                        file_paths=remaining_files, parallel=True
                    )
                    for original, resolved in zip(remaining_originals, remaining_files):
                        results[original] = markitdown_results.get(
                            resolved, f"Failed to read file: {resolved}"
                        )
                
                return results
        except Exception as e:
            return f"Error reading file(s): {e}"
