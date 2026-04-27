from dataclasses import dataclass, field
import subprocess
import re
from typing import Dict, List, Optional



class CommandFailure(Exception):
    pass        
@dataclass
class AgentCommandOutput:
    stdout:str  = ""
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
    
    
    
    def is_safe(self)->bool:
        # 1. Validar Binario
        if self.binary.lower() in AgentCommand._FORBIDDEN_BINARIES:
            return False, f"Security Thread: The binary '{self.binary}' is not allowed."

        # 2. Validar Patrones en Argumentos y Scripts
        full_command = f"{" ".join(self.args)} {self.inline_script}"
        for pattern in AgentCommand._DANGEROUS_PATTERNS:
            if re.search(pattern, full_command):
                return False, f"Security Thread: The args {" ".join(self.args)} may contain dangerous patterns."
        return True, "The binary and its args are safe"
    
    
    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['AgentCommand']:
        if not data or not data.get("binary"):
            return None
        return cls(
            binary=data["binary"],
            args=data.get("args", []),
            inline_script=data.get("inline_script", "")
        )
        
    def execute(self)->AgentCommandOutput:
         # Capa de Seguridad Pre-Ejecución
        is_safe, message = self.is_safe()
        if not is_safe:
            print( f"SECURITY_REFUSAL: {message}")
            return AgentCommandOutput(stdout=None, stderr=None, is_safe=message)
        try:
            if self.inline_script:
                # Execute inline scripts (Python/Bash) via stdin
                process = subprocess.Popen(
                    [self.binary] + self.args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input = self.inline_script)
                return AgentCommandOutput(stdout=stdout, stderr=stderr, is_safe=message )
            else:
                # Execute standard binary + args
                result = subprocess.run(
                    [self.binary] + self.args,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                stdout, stderr = result.stdout, result.stderr
                return AgentCommandOutput(stdout=stdout, stderr=stderr, is_safe=message )
        except Exception as e:
            raise CommandFailure
        
