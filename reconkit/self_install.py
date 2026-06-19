import os
import platform
import stat
import subprocess
from pathlib import Path

from .ui import C, color


PATH_BLOCK_BEGIN = "# >>> ReconKit bin PATH >>>"
PATH_BLOCK_END = "# <<< ReconKit bin PATH <<<"


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def launcher_content(repo_root: Path) -> str:
    return f'''#!/usr/bin/env sh
cd "{repo_root}"
exec python3 "{repo_root / 'recon.py'}" "$@"
'''


def windows_cmd_content(repo_root: Path) -> str:
    return f'''@echo off
cd /d "{repo_root}"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "{repo_root / 'recon.py'}" %*
) else (
  python "{repo_root / 'recon.py'}" %*
)
exit /b %errorlevel%
'''


def windows_ps1_content(repo_root: Path) -> str:
    return f'''Set-Location -LiteralPath "{repo_root}"
if (Get-Command py -ErrorAction SilentlyContinue) {{
  & py -3 "{repo_root / 'recon.py'}" @args
}} else {{
  & python "{repo_root / 'recon.py'}" @args
}}
exit $LASTEXITCODE
'''


def candidate_bin_dirs() -> list[Path]:
    home = Path.home()
    if is_windows():
        return [home / "AppData" / "Local" / "Microsoft" / "WindowsApps", home / ".reconkit" / "bin"]
    return [Path("/usr/local/bin"), home / ".local" / "bin"]


def path_entries() -> list[Path]:
    return [Path(item) for item in os.environ.get("PATH", "").split(os.pathsep) if item]


def path_has(directory: Path) -> bool:
    return str(directory) in os.environ.get("PATH", "").split(os.pathsep)


def first_path_command(name: str) -> Path | None:
    names = (f"{name}.cmd", f"{name}.ps1", name) if is_windows() else (name,)
    for directory in path_entries():
        for item_name in names:
            candidate = directory / item_name
            if candidate.exists() or candidate.is_symlink():
                return candidate
    return None


def is_executable_file(path: Path) -> bool:
    try:
        return path.exists() and (is_windows() or os.access(path, os.X_OK))
    except OSError:
        return False


def ensure_windows_user_path(directory: Path, *, colorize: bool = True) -> None:
    directory = directory.expanduser()
    os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
    try:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "$dir = [Environment]::GetFullPath('" + str(directory).replace("'", "''") + "');"
                "$old = [Environment]::GetEnvironmentVariable('Path','User');"
                "if (($old -split ';') -notcontains $dir) {"
                "[Environment]::SetEnvironmentVariable('Path', ($dir + ';' + $old).TrimEnd(';'), 'User') }"
            ),
        ]
        subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(color(f"[+] Added {directory} to Windows User PATH", C.GREEN, colorize))
    except OSError:
        print(color(f"[!] Could not update Windows User PATH automatically. Add manually: {directory}", C.YELLOW, colorize))


def ensure_local_bin_path(directory: Path, *, colorize: bool = True, prepend: bool = True) -> None:
    directory = directory.expanduser()
    if is_windows():
        ensure_windows_user_path(directory, colorize=colorize)
        return
    if not path_has(directory):
        if prepend:
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
        else:
            os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(directory)
    rc = Path.home() / ".bashrc"
    line = f'export PATH="{directory}:$PATH"' if prepend else f'export PATH="$PATH:{directory}"'
    block = f"{PATH_BLOCK_BEGIN}\n{line}\n{PATH_BLOCK_END}\n"
    original = rc.read_text(encoding="utf-8") if rc.exists() else ""
    if PATH_BLOCK_BEGIN in original and PATH_BLOCK_END in original:
        before, rest = original.split(PATH_BLOCK_BEGIN, 1)
        _, after = rest.split(PATH_BLOCK_END, 1)
        updated = before.rstrip() + "\n" + block + after.lstrip("\n")
    else:
        updated = original.rstrip() + "\n\n" + block
    if updated != original:
        if rc.exists():
            rc.with_suffix(rc.suffix + ".reconkit.bak").write_text(original, encoding="utf-8")
        rc.write_text(updated, encoding="utf-8")
        print(color(f"[+] Added {directory} to PATH in {rc}", C.GREEN, colorize))


def write_launcher(target: Path, repo_root: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if is_windows():
        cmd_target = target.with_suffix(".cmd")
        ps1_target = target.with_suffix(".ps1")
        for item in (cmd_target, ps1_target):
            if item.exists() or item.is_symlink():
                item.unlink()
        cmd_target.write_text(windows_cmd_content(repo_root), encoding="utf-8")
        ps1_target.write_text(windows_ps1_content(repo_root), encoding="utf-8")
        return cmd_target
    if target.exists() or target.is_symlink():
        target.unlink()
    target.write_text(launcher_content(repo_root), encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target


def install_command_entry(name: str = "reconkit", *, prefer_user: bool = False, colorize: bool = True) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    dirs = candidate_bin_dirs()
    if prefer_user and not is_windows():
        dirs = [Path.home() / ".local" / "bin", Path("/usr/local/bin")]
    elif prefer_user and is_windows():
        dirs = [Path.home() / ".reconkit" / "bin", Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps"]

    first_existing = first_path_command(name)
    install_dir = dirs[0]
    if first_existing and first_existing.parent in dirs and not prefer_user:
        install_dir = first_existing.parent

    try:
        installed = write_launcher(install_dir / name, repo_root)
        ensure_local_bin_path(installed.parent, colorize=colorize, prepend=True)
    except OSError as exc:
        fallback_dir = (Path.home() / ".reconkit" / "bin") if is_windows() else (Path.home() / ".local" / "bin")
        try:
            installed = write_launcher(fallback_dir / name, repo_root)
            ensure_local_bin_path(installed.parent, colorize=colorize, prepend=True)
        except OSError as fallback_exc:
            print(color(f"[!] Could not install reconkit command: {fallback_exc}", C.RED, colorize))
            print(color(f"    Original error: {exc}", C.YELLOW, colorize))
            return 1

    shadow = first_path_command(name)
    if shadow and shadow != installed and not is_executable_file(shadow):
        print(color(f"[!] Found broken reconkit earlier in PATH: {shadow}", C.YELLOW, colorize))
        print(color(f"    Remove/fix it if your shell still opens the wrong one.", C.YELLOW, colorize))
        print(color(f"    Current install is OK: {installed}", C.GREEN, colorize))
    elif shadow and shadow != installed:
        print(color(f"[!] Another reconkit appears earlier in PATH: {shadow}", C.YELLOW, colorize))
        print(color(f"    Prefer this one if needed: {installed}", C.YELLOW, colorize))

    print(color(f"[+] Installed command: {installed}", C.GREEN, colorize))
    print(color("[+] Try now: reconkit", C.CYAN, colorize))
    if is_windows():
        print(color("    If the current terminal cannot find it, open a new PowerShell window.", C.DIM, colorize))
    return 0
