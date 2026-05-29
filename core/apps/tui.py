"""
Code browser example.

Run with:

    python code_browser.py PATH
"""

from __future__ import annotations

import sys
import os
import asyncio
import logging
import gc
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from rich.traceback import Traceback
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.highlight import highlight
from textual.reactive import reactive, var
from textual.widgets import DirectoryTree, Footer, Header, Input, Static, Log
from textual.worker import Worker
from textual import work

from core.session.session import Session, Model
from core.requests.request import ChesterRequest
from core.task.task import Task, Message, InfoMessage, AgentMessage, ErrorMessage, ApprovalMessage, NeedsUserInputMessage
from core.mcp.mcp_manager import MCPManager
from core.mcp.mcp_server_config import StdioMCPServerConfiguration
from core.clients.clients import get_client
from core.agents.agents import Architect
from core.skill.skill import Skill
import asyncio

class TextualLogHandler(logging.Handler):
    """Custom logging handler to redirect logs to a Textual Log widget."""
    def __init__(self, log_widget: Log):
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record):
        msg = self.format(record)
        try:
            # Attempt to call from thread if we're in a background thread
            self.log_widget.app.call_from_thread(self.log_widget.write_line, msg)
        except RuntimeError:
            # If we're already in the main thread, call directly
            self.log_widget.write_line(msg)

class CodeBrowser(App):

    """Textual code browser app with Chester Agent integration."""

    CSS_PATH = "code_browser.tcss"
    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("q", "quit", "Quit"),
    ]

    show_tree = var(True)
    path: reactive[str | None] = reactive(None)
    
    session: var[Optional[Session]] = var(None)
    che_request: var[Optional[ChesterRequest]] = var(None)
    mcp_manager: var[Optional[MCPManager]] = var(None)
    waiting_for_session_selection: var[bool] = var(False)
    available_sessions: var[List[Dict[str, str]]] = var([])

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        # Removed: path = "./" if len(sys.argv) < 2 else sys.argv[1]
        yield Header()
        with Container():
            # yield DirectoryTree("./", id="tree-view")
            with VerticalScroll(id="code-view"):
                yield Log(id="chat-log", max_lines=1000)
                yield Log(id="agent-logs", max_lines=500)
                yield Static(id="code", expand=True)
            yield Input(
                placeholder="Type your task or response here...",
                id="user-input"
            )
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one("#user-input").focus()
        
        # Setup logging redirection
        agent_log_widget = self.query_one("#agent-logs", Log)
        handler = TextualLogHandler(agent_log_widget)
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
        # Add handler to the core logger to capture agent activities
        core_logger = logging.getLogger("core")
        core_logger.addHandler(handler)
        core_logger.setLevel(logging.INFO)

        self.available_sessions = Session.get_selectable_sessions()
        if not self.available_sessions:
            self.log_message("System: No previous sessions found. Starting a new session.")
            await self._initialize_session_and_request(session_id=None)
        else:
            self.log_message("System: Select a session to resume or create a new one:")
            for i, session_info in enumerate(self.available_sessions):
                self.log_message(f"[{i+1}] {session_info['label']}")
            self.log_message("[0] Create New Session")
            
            input_widget = self.query_one("#user-input", Input)
            input_widget.placeholder = "Enter session number or '0' for new session..."
            input_widget.add_class("needs-attention")
            self.waiting_for_session_selection = True

    async def _initialize_session_and_request(self, session_id: Optional[str]) -> None:
        self.session = Session.find_or_create(session_id=session_id)
        
        # Resume session history if not new
        if not self.session.is_new:
            self.log_message(f"System: Resuming session {self.session.id}")
            for content in self.session.history:
                role = content.role
                parts_text = []
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        parts_text.append(part.text)
                
                text = " ".join(parts_text)
                if not text:
                    continue
                
                if role == 'user':
                    self.log_message(f"User: {text}")
                elif role == 'model':
                    self.log_message(f"Chester: {text}")
            
            # Update UI state based on last response
            input_widget = self.query_one("#user-input", Input)
            if self.session.last_response.needs_approval:
                self.log_message("System: Approve command? (yes/no)")
                input_widget.placeholder = "Approve? (yes/no) or explain why not..."
                input_widget.add_class("needs-attention")
            elif self.session.last_response.needs_user_information:
                prompt = self.session.last_response.response_to_user or "Chester needs more information."
                self.log_message(f"Chester needs information: {prompt}")
                input_widget.placeholder = "Provide the requested information..."
                input_widget.add_class("needs-attention")

        self.session.add_skill(Skill(name='unix-file-manipulation'))
        
        # Default LLM client
        selected_model = Model.gemini_2_5_flash
        client = get_client(provider="gemini", model=selected_model)
        mcp_server_config = StdioMCPServerConfiguration(config_json='config/mcp_servers.json')
        self.mcp_manager = MCPManager(mcp_server_config)
        
        self.che_request = ChesterRequest(
            user_approval=False,
            user_response='',
            master_client= selected_model,
            clients={selected_model: client},
            mcp_manager=self.mcp_manager,
            provider='gemini',
            model=selected_model.value,
            turn=self.session.turn
        )
        
        if self.session.is_new:
            self.log_message("System: Chester initialized. Ready for tasks.")
        else:
            self.log_message(f"System: Session {self.session.id} loaded. Ready for tasks.")
        self.query_one("#user-input").focus()


    def log_message(self, message: str) -> None:
        self.query_one("#chat-log", Log).write_line(message)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value
        if not user_input:
            return

        event.input.value = ""
        self.log_message(f"User: {user_input}")

        input_widget = self.query_one("#user-input", Input)
        input_widget.placeholder = "Type your task or response here..."
        input_widget.remove_class("needs-attention")

        if self.waiting_for_session_selection:
            try:
                selection = int(user_input)
                if selection == 0:
                    session_id_to_load = None
                    self.log_message("System: Creating a new session.")
                elif 1 <= selection <= len(self.available_sessions):
                    session_id_to_load = self.available_sessions[selection - 1]['id']
                    self.log_message(f"System: Selected session {session_id_to_load}.")
                else:
                    self.log_message("System: Invalid selection. Please enter a valid number or '0'.")
                    input_widget.add_class("needs-attention")
                    return
                
                await self._initialize_session_and_request(session_id_to_load)
                self.waiting_for_session_selection = False
            except ValueError:
                self.log_message("System: Invalid input. Please enter a number.")
                input_widget.add_class("needs-attention")
            return
        
        # Original logic for task submission
        if self.session.last_response and self.session.last_response.needs_approval:
            self.che_request.user_approval = True if user_input.lower() in ['yes', 'y'] else False
            # If disapproved, we might want to pass the reason why
            if not self.che_request.user_approval and user_input.lower() not in ['no', 'n']:
                self.che_request.user_response = f"No, because: {user_input}"
            self.run_agent_task()
        elif self.session.last_response and self.session.last_response.needs_user_information and not self.session.last_response.is_complete:
            self.che_request.user_response = user_input
            self.run_agent_task()
        else:
            # New task
            self.che_request.user_task = user_input
            self.che_request.user_response = ""
            self.che_request.set_system_instructions(
               Architect(
                    task=user_input,
                    skills=[Skill(name=skill_name) for skill_name in Skill.all_names()],
                    available_mcps=StdioMCPServerConfiguration.get_descriptions(
                        self.mcp_manager.config),
                    path=os.getcwd(),
                    model=Model.gemini_2_5_flash
                ).to_prompt()
            )
            self.run_agent_task()

    @work(exclusive=True)
    async def run_agent_task(self) -> None:
        self.log_message("System: Processing...")
        agent_logs = self.query_one("#agent-logs", Log)
        agent_logs.clear()
        agent_logs.add_class("visible")

        last_assistant_msg = ""
        try:
            async for message in Task.run(session=self.session, request=self.che_request):
                if isinstance(message, InfoMessage):
                    # Info messages go to chat log with System prefix
                    self.log_message(f"System: {message.text}")
                elif isinstance(message, AgentMessage):
                    # Agent thoughts go to the secondary log
                    agent_logs.write_line(message.text)
                    last_assistant_msg = message.text
                elif isinstance(message, ErrorMessage):
                    self.log_message(f"Error: {message.text}")
                elif isinstance(message, (ApprovalMessage, NeedsUserInputMessage)):
                    # Direct requests to user
                    self.log_message(f"Chester: {message.text}")
                elif isinstance(message, str):
                    last_assistant_msg = message
                else:
                    # Fallback for any other message types
                    agent_logs.write_line(str(message))

            # After streaming finished, log the final assistant message to chat-log if we haven't already
            
            if self.session.last_response.response_to_user:
                self.log_message(f"Chester: {self.session.last_response.response_to_user}")
            elif last_assistant_msg:
                self.log_message(f"Chester: {last_assistant_msg}")

            input_widget = self.query_one("#user-input", Input)
            if self.session.last_response.is_complete:
                self.log_message("System: Task completed.")
                self.che_request.user_response = ""
                self.che_request.user_task = ""
                input_widget.placeholder = "Type your next task..."
            elif self.session.last_response.needs_approval:
                self.log_message("System: Approve command? (yes/no)")
                input_widget.placeholder = "Approve? (yes/no) or explain why not..."
                input_widget.add_class("needs-attention")
            elif self.session.last_response.needs_user_information:
                prompt = self.session.last_response.response_to_user or "Chester needs more information."
                self.log_message(f"Chester needs information: {prompt}")
                input_widget.placeholder = "Provide the requested information..."
                input_widget.add_class("needs-attention")

            input_widget.focus()
        except Exception as e:
            self.log_message(f"Error: {str(e)}")
            import traceback
            self.log_message(traceback.format_exc())
        finally:
            agent_logs.remove_class("visible")
            # Explicitly free memory after heavy task
            gc.collect()



    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Called when the user click a file in the directory tree."""
        event.stop()
        self.path = str(event.path)
        self.set_class(True, "-show-code")
        self.query_one("#user-input").focus()

    @work(exclusive=True, thread=True)
    def watch_path(self, path: str | None) -> None:
        """Called when path changes. Performs highlighting in a thread."""
        code_view = self.query_one("#code", Static)
        if path is None:
            self.app.call_from_thread(code_view.update, "")
            return
        try:
            code = Path(path).read_text(encoding="utf-8")
            syntax = highlight(code, path=path)
        except Exception:
            self.app.call_from_thread(code_view.update, Traceback(theme="github-dark", width=None))
            self.sub_title = "ERROR"
        else:
            self.app.call_from_thread(code_view.update, syntax)
            self.app.call_from_thread(self.query_one("#code-view").scroll_home, animate=False)
            self.sub_title = path

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""
        self.show_tree = not self.show_tree

    async def action_quit(self) -> None:
        if self.mcp_manager:
            await self.mcp_manager.cleanup()
        self.exit()

if __name__ == "__main__":
    
    load_dotenv()
    CodeBrowser().run()