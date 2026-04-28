from dataclasses import dataclass, field
import json
import subprocess
import logging
import re
from typing import Dict, List, Mapping, Optional


from core.mcp_client import MCPToolCall, StdioMCPClient
from core.mcp_manager import MCPManager
from mcp.types import Tool, CallToolResult


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class CommandFailure(Exception):
    pass


@dataclass
class AgentCommandOutput:
    stdout: str = ""
    stderr: str = ""
    is_safe: str = ""


@dataclass
class AgentCommand:

    _FORBIDDEN_BINARIES = {"rm", "chmod",
                           "chown", "su", "sudo", "format", "mkfs"}
    _DANGEROUS_PATTERNS = [
        r"-rf",          # Borrado recursivo forzado
        r"/\s*$",        # Targeting raíz /
        r"/etc",         # Archivos de sistema
        r"\.\./",        # Path traversal (intentar salir del workspace)
        r"777",          # Permisos universales
    ]

    binary: str = ""
    args: List[str] = field(default_factory=list)
    inline_script: str = ""
    mcp_call: Optional[MCPToolCall] = None

    def is_safe(self) -> bool:
        if self.mcp_call:
            return True, "MCP call is safe"

        if self.binary and self.binary.lower() in AgentCommand._FORBIDDEN_BINARIES:
            return False, f"Security Thread: The binary '{self.binary}' is not allowed."

        # 2. Validar Patrones en Argumentos y Scripts
        full_command = f"{" ".join(self.args)} {self.inline_script}"
        for pattern in AgentCommand._DANGEROUS_PATTERNS:
            if re.search(pattern, full_command):
                return False, f"Security Thread: The args {" ".join(self.args)} may contain dangerous patterns."
        return True, "The binary and its args are safe"

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['AgentCommand']:
        if not data or len(data.keys()) == 0:
            return None

        mcp_data = data.get("mcp_call", None)

        return cls(
            binary=data.get("binary", None),
            args=data.get("args", []),
            inline_script=data.get("inline_script", ""),
            mcp_call=MCPToolCall(**mcp_data) if mcp_data else None
        )

    async def execute(self, mcp_manager: MCPManager) -> AgentCommandOutput:
        is_safe, message = self.is_safe()
        if not is_safe:
            logger.info(f"SECURITY_REFUSAL: {message}")
            return AgentCommandOutput(stdout=None, stderr=None, is_safe=message)
        try:
            if self.mcp_call:
                try:
                    session = await mcp_manager.get_session(self.mcp_call.server_name)

                    if not session:
                        return f"ERROR: MCP Server '{self.mcp_call.server_name}' not connected."

                    logger.info(
                        f"🔌 Calling MCP Tool: {self.mcp_call.tool_name} on {self.mcp_call.server_name}")
                    result = await session.call_tool(self.mcp_call.tool_name, arguments=self.mcp_call.arguments)
                    if isinstance(result, CallToolResult):
                        return AgentCommandOutput(stdout=StdioMCPClient.sanitize_mcp_content(result.content[0].text))
                    else:
                        return AgentCommandOutput(stdout=f"{result}", stderr="", is_safe=message)
                except Exception as e:
                    return AgentCommandOutput(stdout="", stderr=str(e))
            elif self.inline_script:
                # Execute inline scripts (Python/Bash) via stdin
                process = subprocess.Popen(
                    [self.binary] + self.args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=self.inline_script)
                return AgentCommandOutput(stdout=stdout, stderr=stderr, is_safe=message)
            else:
                # Execute standard binary + args
                result = subprocess.run(
                    [self.binary] + self.args,
                    capture_output=True,
                    text=True,
                    timeout=60 * 2
                )
                stdout, stderr = result.stdout, result.stderr
                return AgentCommandOutput(stdout=stdout, stderr=stderr, is_safe=message)
        except Exception:
            raise CommandFailure(self)
