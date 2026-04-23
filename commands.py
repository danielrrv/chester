import subprocess
import re

class SecurityGuard:
    """Middleware de seguridad para validar comandos."""

    FORBIDDEN_BINARIES = {"rm", "chmod",
        "chown", "su", "sudo", "format", "mkfs"}
    DANGEROUS_PATTERNS = [
        r"-rf",          # Borrado recursivo forzado
        r"/\s*$",        # Targeting raíz /
        r"/etc",         # Archivos de sistema
        r"\.\./",        # Path traversal (intentar salir del workspace)
        r"777",          # Permisos universales
    ]

    @staticmethod
    def is_safe(command_json):
        binary = command_json.get("binary", "").lower()
        args = " ".join(command_json.get("args", [])).lower()
        script = command_json.get("inline_script", "").lower()

        # 1. Validar Binario
        if binary in SecurityGuard.FORBIDDEN_BINARIES:
            return False, f"Seguridad: El binario '{binary}' está estrictamente prohibido."

        # 2. Validar Patrones en Argumentos y Scripts
        full_command = f"{args} {script}"
        for pattern in SecurityGuard.DANGEROUS_PATTERNS:
            if re.search(pattern, full_command):
                return False, f"Seguridad: Patrón peligroso detectado: '{pattern}'"

        return True, "Safe"


def execute_protected_command(command_json):
    # Capa de Seguridad Pre-Ejecución
    is_safe, message = SecurityGuard.is_safe(command_json)
    if not is_safe:
        return f"SECURITY_REFUSAL: {message}"
    
    inline_script = command_json.get("inline_script", "")
    args = command_json.get("args", [])
    binary = command_json.get("binary")
    
    # Ejecución Real (Solo si pasó la seguridad)
    try:
        if inline_script:
            # Execute inline scripts (Python/Bash) via stdin
            process = subprocess.Popen(
                [binary] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=inline_script)
        else:
            # Execute standard binary + args
            result = subprocess.run(
                [binary] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            stdout, stderr = result.stdout, result.stderr
        return f"STDOUT: {stdout}\nSTDERR: {stderr}"
    except Exception as e:
        return f"EXECUTION_ERROR: {str(e)}"
    
