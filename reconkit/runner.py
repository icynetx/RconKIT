import os
import shutil
import subprocess
import time
from pathlib import Path

from .models import CmdResult

TOOL_ALIASES = {
    "httpx": ("httpx", "httpx-toolkit"),
    "httpx-toolkit": ("httpx-toolkit", "httpx"),
    "testssl.sh": ("testssl.sh", "testssl"),
}


def go_bin_dirs() -> list[Path]:
    dirs = []
    if os.environ.get("GOBIN"):
        dirs.append(Path(os.environ["GOBIN"]).expanduser())
    if os.environ.get("GOPATH"):
        dirs.append(Path(os.environ["GOPATH"]).expanduser() / "bin")
    dirs.append(Path.home() / "go" / "bin")
    return dirs


def executable_names(name: str) -> tuple[str, ...]:
    return (name,)


def extra_tool_dirs() -> list[Path]:
    return list(dict.fromkeys(go_bin_dirs()))


def which_tool(name: str) -> str | None:
    for candidate_name in TOOL_ALIASES.get(name, (name,)):
        for executable_name in executable_names(candidate_name):
            found = shutil.which(executable_name)
            if found:
                return found
            for directory in extra_tool_dirs():
                candidate = directory / executable_name
                if candidate.exists() and os.access(candidate, os.X_OK):
                    return str(candidate)
    return None


def command_exists(name: str) -> bool:
    return which_tool(name) is not None


def run_cmd(command: list[str], timeout: int) -> CmdResult:
    start = time.monotonic()
    executable = which_tool(command[0])
    if not executable:
        return CmdResult(command=command, ok=False, missing=True, stderr=f"{command[0]} not found")
    actual_command = [executable, *command[1:]]
    try:
        proc = subprocess.run(actual_command, capture_output=True, text=True, timeout=timeout, check=False)
        return CmdResult(
            command=command,
            ok=proc.returncode == 0,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            elapsed=time.monotonic() - start,
        )
    except subprocess.TimeoutExpired as exc:
        return CmdResult(
            command=command,
            ok=False,
            stdout=(exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            stderr=f"Timed out after {timeout}s",
            elapsed=time.monotonic() - start,
        )
