import os
import stat
from pathlib import Path

from .ui import C, color


PATH_BLOCK_BEGIN = "# >>> ReconKit bin PATH >>>"
PATH_BLOCK_END = "# <<< ReconKit bin PATH <<<"


def launcher_content(repo_root: Path) -> str:
    return f'''#!/usr/bin/env sh
cd "{repo_root}"
exec python3 "{repo_root / 'recon.py'}" "$@"
'''


def candidate_bin_dirs() -> list[Path]:
    home = Path.home()
    return [Path("/usr/local/bin"), home / ".local" / "bin"]


def path_entries() -> list[Path]:
    return [Path(item) for item in os.environ.get("PATH", "").split(os.pathsep) if item]


def path_has(directory: Path) -> bool:
    return str(directory) in os.environ.get("PATH", "").split(os.pathsep)


def first_path_command(name: str) -> Path | None:
    names = (name,)
    for directory in path_entries():
        for item_name in names:
            candidate = directory / item_name
            if candidate.exists() or candidate.is_symlink():
                return candidate
    return None


def is_executable_file(path: Path) -> bool:
    try:
        return path.exists() and os.access(path, os.X_OK)
    except OSError:
        return False


def ensure_local_bin_path(directory: Path, *, colorize: bool = True, prepend: bool = True) -> None:
    directory = directory.expanduser()
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
    if target.exists() or target.is_symlink():
        target.unlink()
    target.write_text(launcher_content(repo_root), encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target


def install_command_entry(name: str = "reconkit", *, prefer_user: bool = False, colorize: bool = True) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    dirs = candidate_bin_dirs()
    if prefer_user:
        dirs = [Path.home() / ".local" / "bin", Path("/usr/local/bin")]

    first_existing = first_path_command(name)
    install_dir = dirs[0]
    if first_existing and first_existing.parent in dirs and not prefer_user:
        install_dir = first_existing.parent

    try:
        installed = write_launcher(install_dir / name, repo_root)
        ensure_local_bin_path(installed.parent, colorize=colorize, prepend=True)
    except OSError as exc:
        fallback_dir = Path.home() / ".local" / "bin"
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
    return 0


def remove_path_block(*, colorize: bool = True) -> bool:
    rc = Path.home() / ".bashrc"
    if not rc.exists():
        return False
    original = rc.read_text(encoding="utf-8")
    if PATH_BLOCK_BEGIN not in original or PATH_BLOCK_END not in original:
        return False
    before, rest = original.split(PATH_BLOCK_BEGIN, 1)
    _, after = rest.split(PATH_BLOCK_END, 1)
    updated = before.rstrip() + "\n" + after.lstrip("\n")
    rc.with_suffix(rc.suffix + ".reconkit-uninstall.bak").write_text(original, encoding="utf-8")
    rc.write_text(updated.rstrip() + "\n", encoding="utf-8")
    print(color(f"[+] Removed ReconKit PATH block from {rc}", C.GREEN, colorize))
    return True


def launcher_targets(name: str = "reconkit") -> list[Path]:
    targets: list[Path] = []
    for directory in candidate_bin_dirs():
        target = directory / name
        if target not in targets:
            targets.append(target)
    first = first_path_command(name)
    if first and first not in targets:
        targets.append(first)
    return targets


def launcher_points_to_reconkit(path: Path) -> bool:
    try:
        if path.is_symlink():
            resolved = path.resolve(strict=False)
            return "reconkit" in str(resolved).lower() or "rconkit" in str(resolved).lower()
        if not path.exists() or not path.is_file():
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")[:1200]
    except OSError:
        return False
    return "recon.py" in text and ("ReconKit" in text or ".reconkit" in text or "reconkit" in text.lower())


def uninstall_command_entry(name: str = "reconkit", *, purge: bool = False, dry_run: bool = False, colorize: bool = True) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    removed = 0
    for target in launcher_targets(name):
        if not (target.exists() or target.is_symlink()):
            continue
        if not launcher_points_to_reconkit(target):
            print(color(f"[!] Skipping non-ReconKit command: {target}", C.YELLOW, colorize))
            continue
        if dry_run:
            print(color(f"[*] Would remove command: {target}", C.CYAN, colorize))
        else:
            try:
                target.unlink()
                removed += 1
                print(color(f"[+] Removed command: {target}", C.GREEN, colorize))
            except OSError as exc:
                print(color(f"[!] Could not remove {target}: {exc}", C.RED, colorize))
                return 1
    if dry_run:
        print(color(f"[*] Would remove ReconKit PATH block from ~/.bashrc if present", C.CYAN, colorize))
    else:
        remove_path_block(colorize=colorize)

    if purge:
        purge_targets = [repo_root / "recon_config.json", repo_root / "recon_presets.json"]
        home_root = Path.home() / ".reconkit"
        for item in purge_targets:
            if item.exists():
                if dry_run:
                    print(color(f"[*] Would remove data file: {item}", C.CYAN, colorize))
                else:
                    item.unlink()
                    print(color(f"[+] Removed data file: {item}", C.GREEN, colorize))
        try:
            repo_inside_home_root = repo_root.resolve().is_relative_to(home_root.resolve())
        except OSError:
            repo_inside_home_root = False
        if home_root.exists() and repo_inside_home_root:
            if dry_run:
                print(color(f"[*] Would remove install directory: {home_root}", C.CYAN, colorize))
            else:
                import shutil
                shutil.rmtree(home_root)
                print(color(f"[+] Removed install directory: {home_root}", C.GREEN, colorize))

    if dry_run:
        print(color("[+] Uninstall dry-run complete.", C.GREEN, colorize))
    elif removed == 0:
        print(color("[!] No ReconKit command launcher was found to remove.", C.YELLOW, colorize))
    else:
        print(color("[+] ReconKit command uninstall complete. Open a new terminal if your shell cached the command.", C.GREEN, colorize))
    return 0
