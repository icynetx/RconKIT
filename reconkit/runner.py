import os
import platform
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
    if os.environ.get("USERPROFILE"):
        dirs.append(Path(os.environ["USERPROFILE"]) / "go" / "bin")
    return dirs


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def executable_names(name: str) -> tuple[str, ...]:
    if not is_windows() or Path(name).suffix:
        return (name,)
    return (name, f"{name}.exe", f"{name}.cmd", f"{name}.bat", f"{name}.ps1")


def extra_tool_dirs() -> list[Path]:
    dirs = go_bin_dirs()
    if is_windows():
        profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
        dirs.extend(
            [
                Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Go" / "bin",
                profile / "AppData" / "Local" / "Microsoft" / "WindowsApps",
                profile / ".reconkit" / "bin",
            ]
        )
    return list(dict.fromkeys(dirs))


def which_tool(name: str) -> str | None:
    for candidate_name in TOOL_ALIASES.get(name, (name,)):
        for executable_name in executable_names(candidate_name):
            found = shutil.which(executable_name)
            if found:
                return found
            for directory in extra_tool_dirs():
                candidate = directory / executable_name
                if candidate.exists() and (is_windows() or os.access(candidate, os.X_OK)):
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
