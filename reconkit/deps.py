import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .constants import OPTIONAL_TOOLS, REQUIRED_TOOLS
from .runner import command_exists, executable_names
from .ui import C, color, hr, table


@dataclass(frozen=True)
class InstallPlan:
    tool: str
    kind: str
    provider: str
    command: list[str]
    note: str = ""


NATIVE_PACKAGES: dict[str, dict[str, str | None]] = {
    "apt": {
        "nmap": "nmap", "dig": "dnsutils", "host": "bind9-host", "nslookup": "dnsutils", "whois": "whois",
        "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto",
        "testssl.sh": "testssl.sh", "amass": None, "curl": "curl", "jq": "jq",
        "httpx": None, "httpx-toolkit": None, "subfinder": None, "dnsx": None, "katana": None, "gowitness": None, "nuclei": None,
    },
    "dnf": {
        "nmap": "nmap", "dig": "bind-utils", "host": "bind-utils", "nslookup": "bind-utils", "whois": "whois",
        "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto",
        "testssl.sh": "testssl", "amass": None, "curl": "curl", "jq": "jq",
        "httpx": None, "httpx-toolkit": None, "subfinder": None, "dnsx": None, "katana": None, "gowitness": None, "nuclei": None,
    },
    "pacman": {
        "nmap": "nmap", "dig": "bind", "host": "bind", "nslookup": "bind", "whois": "whois",
        "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto",
        "testssl.sh": "testssl.sh", "httpx": "httpx", "httpx-toolkit": "httpx", "subfinder": "subfinder",
        "amass": "amass", "dnsx": "dnsx", "katana": "katana", "gowitness": "gowitness", "nuclei": "nuclei", "curl": "curl", "jq": "jq",
    },
    "apk": {
        "nmap": "nmap", "dig": "bind-tools", "host": "bind-tools", "nslookup": "bind-tools", "whois": "whois",
        "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto",
        "testssl.sh": "testssl", "httpx": "httpx", "httpx-toolkit": "httpx", "curl": "curl", "jq": "jq",
        "subfinder": None, "amass": None, "dnsx": None, "katana": None, "gowitness": None, "nuclei": None,
    },
    "brew": {
        "nmap": "nmap", "dig": "bind", "host": "bind", "nslookup": "bind", "whois": "whois",
        "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto", "testssl.sh": "testssl",
        "httpx": "projectdiscovery/tap/httpx", "httpx-toolkit": "projectdiscovery/tap/httpx",
        "subfinder": "projectdiscovery/tap/subfinder", "dnsx": "projectdiscovery/tap/dnsx", "katana": "projectdiscovery/tap/katana",
        "nuclei": "projectdiscovery/tap/nuclei", "amass": "amass", "gowitness": "gowitness", "curl": "curl", "jq": "jq",
    },
    "choco": {
        "nmap": "nmap", "whois": "whois", "curl": "curl", "jq": "jq", "amass": "amass", "nuclei": "nuclei", "git": "git", "go": "golang", "python": "python",
        "dig": None, "host": None, "nslookup": None, "whatweb": None, "wafw00f": None, "sslscan": None, "nikto": None,
        "httpx": None, "httpx-toolkit": None, "testssl.sh": None, "subfinder": None, "dnsx": None, "katana": None, "gowitness": None,
    },
    "winget": {
        "nmap": "Insecure.Nmap", "curl": "cURL.cURL", "jq": "jqlang.jq", "git": "Git.Git", "go": "GoLang.Go", "python": "Python.Python.3.12",
        "dig": None, "host": None, "nslookup": None, "whois": None, "whatweb": None, "wafw00f": None, "sslscan": None,
        "nikto": None, "httpx": None, "httpx-toolkit": None, "testssl.sh": None, "subfinder": None, "amass": None,
        "dnsx": None, "katana": None, "gowitness": None, "nuclei": None,
    },
}

GO_INSTALLS = {
    "httpx": "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "httpx-toolkit": "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "subfinder": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    "dnsx": "github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
    "katana": "github.com/projectdiscovery/katana/cmd/katana@latest",
    "nuclei": "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    "gowitness": "github.com/sensepost/gowitness@latest",
    "amass": "github.com/owasp-amass/amass/v4/...@master",
}

PIPX_INSTALLS = {
    "wafw00f": "wafw00f",
}


TOOL_ALIASES = {
    "httpx": ("httpx", "httpx-toolkit"),
    "httpx-toolkit": ("httpx-toolkit", "httpx"),
    "testssl.sh": ("testssl.sh", "testssl"),
}

GO_BOOTSTRAP_PACKAGES = {
    "apt": "golang-go",
    "dnf": "golang",
    "pacman": "go",
    "apk": "go",
    "brew": "go",
    "choco": "golang",
    "winget": "GoLang.Go",
}

MANUAL_HINTS = {
    "dig": "Install BIND tools. On Windows, prefer WSL/Kali or install BIND utilities manually.",
    "host": "Install BIND tools: bind9-host/dnsutils/bind-utils/bind.",
    "nslookup": "Install BIND tools or Windows DNS utilities.",
    "whatweb": "Install from Linux/macOS packages. On Windows, WSL/Kali is recommended.",
    "sslscan": "Install from Linux/macOS packages. On Windows, WSL/Kali or upstream binaries are recommended.",
    "nikto": "Install from Linux/macOS packages. On Windows, WSL/Kali is recommended.",
    "testssl.sh": "Install from package manager or upstream https://testssl.sh/.",
}


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def sudo_prefix() -> list[str]:
    if is_windows():
        return []
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    if command_exists("sudo"):
        return ["sudo"]
    return []


def available_managers() -> list[str]:
    order = ("apt", "dnf", "pacman", "apk", "brew", "choco", "winget")
    return [manager for manager in order if command_exists(manager)]


def detect_package_manager() -> str | None:
    managers = available_managers()
    return managers[0] if managers else None


def install_one_command(provider: str, package: str) -> list[str]:
    prefix = sudo_prefix()
    if provider == "apt":
        return prefix + ["apt", "install", "-y", package]
    if provider == "dnf":
        return prefix + ["dnf", "install", "-y", package]
    if provider == "pacman":
        return prefix + ["pacman", "-Sy", "--needed", "--noconfirm", package]
    if provider == "apk":
        return prefix + ["apk", "add", package]
    if provider == "brew":
        return ["brew", "install", package]
    if provider == "choco":
        return ["choco", "install", "-y", package]
    if provider == "winget":
        return ["winget", "install", "--id", package, "--accept-package-agreements", "--accept-source-agreements"]
    return []


def provider_update_command(provider: str) -> list[str] | None:
    if provider == "apt":
        return sudo_prefix() + ["apt", "update"]
    if provider == "brew":
        return ["brew", "update"]
    return None


PATH_BLOCK_BEGIN = "# >>> ReconKit PATH >>>"
PATH_BLOCK_END = "# <<< ReconKit PATH <<<"


def current_shell_rc_candidates() -> list[Path]:
    if is_windows():
        return []
    shell = Path(os.environ.get("SHELL", "")).name
    home = Path.home()
    candidates = []
    if shell == "zsh":
        candidates.append(home / ".zshrc")
    elif shell == "fish":
        candidates.append(home / ".config" / "fish" / "config.fish")
    else:
        candidates.append(home / ".bashrc")
    candidates.append(home / ".profile")
    unique = []
    for item in candidates:
        if item not in unique:
            unique.append(item)
    return unique


def path_contains(directory: Path) -> bool:
    directory_text = str(directory.expanduser())
    return directory_text in os.environ.get("PATH", "").split(os.pathsep)


def add_to_current_path(directory: Path) -> None:
    directory_text = str(directory.expanduser())
    if not path_contains(directory):
        os.environ["PATH"] = directory_text + os.pathsep + os.environ.get("PATH", "")


def shell_path_block(directories: list[Path], fish: bool = False) -> str:
    clean_dirs = [str(directory.expanduser()) for directory in directories]
    if fish:
        lines = [PATH_BLOCK_BEGIN]
        for directory in clean_dirs:
            lines.append(f'fish_add_path "{directory}"')
        lines.append(PATH_BLOCK_END)
        return "\n".join(lines) + "\n"
    joined = ":".join(clean_dirs)
    return f'{PATH_BLOCK_BEGIN}\nexport PATH="$PATH:{joined}"\n{PATH_BLOCK_END}\n'


def persist_windows_user_path(directories: list[Path], *, colorize: bool = True) -> None:
    if not directories:
        return
    try:
        existing = os.environ.get("PATH", "").split(os.pathsep)
        for directory in directories:
            text = str(directory.expanduser())
            if text not in existing:
                os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + text
        ps_dirs = ";".join(str(directory.expanduser()).replace("'", "''") for directory in directories)
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "$dirs = '" + ps_dirs + "' -split ';';"
                "$old = [Environment]::GetEnvironmentVariable('Path','User');"
                "$parts = @(); if ($old) { $parts = $old -split ';' | Where-Object { $_ } };"
                "foreach ($dir in $dirs) { if ($dir -and ($parts -notcontains $dir)) { $parts += $dir } };"
                "[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')"
            ),
        ]
        subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(color("[+] Persisted tool directories to Windows User PATH.", C.GREEN, colorize))
        print(color("    Open a new PowerShell/CMD window if an external shell cannot see new tools yet.", C.DIM, colorize))
    except OSError:
        print(color("[!] Could not persist Windows User PATH automatically; current ReconKit run still knows these paths.", C.YELLOW, colorize))


def ensure_path_persisted(directories: list[Path], *, dry_run: bool = False, colorize: bool = True) -> None:
    existing_dirs = [directory.expanduser() for directory in directories if directory.expanduser().exists()]
    if not existing_dirs:
        return
    missing_dirs = [directory for directory in existing_dirs if not path_contains(directory)]
    for directory in existing_dirs:
        add_to_current_path(directory)
    if not missing_dirs:
        return
    if is_windows():
        print(color("[*] Adding Go/ReconKit bin directories to current ReconKit process PATH.", C.CYAN, colorize))
        if dry_run:
            print(color("[*] Would persist missing directories to Windows User PATH.", C.CYAN, colorize))
            return
        persist_windows_user_path(missing_dirs, colorize=colorize)
        return
    rc_candidates = current_shell_rc_candidates()
    if not rc_candidates:
        return
    rc_path = rc_candidates[0]
    fish = rc_path.name == "config.fish"
    block = shell_path_block(missing_dirs, fish=fish)
    if dry_run:
        print(color(f"[*] Would add ReconKit PATH block to {rc_path}: {', '.join(str(d) for d in missing_dirs)}", C.CYAN, colorize))
        return
    rc_path.parent.mkdir(parents=True, exist_ok=True)
    original = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
    if PATH_BLOCK_BEGIN in original and PATH_BLOCK_END in original:
        before, rest = original.split(PATH_BLOCK_BEGIN, 1)
        _, after = rest.split(PATH_BLOCK_END, 1)
        updated = before.rstrip() + "\n" + block + after.lstrip("\n")
    else:
        updated = original.rstrip() + "\n\n" + block
    if updated != original:
        if rc_path.exists():
            backup = rc_path.with_suffix(rc_path.suffix + ".reconkit.bak")
            backup.write_text(original, encoding="utf-8")
        rc_path.write_text(updated, encoding="utf-8")
        print(color(f"[+] Added Go tool PATH to {rc_path}", C.GREEN, colorize))
        print(color("    New terminals will see it automatically; current ReconKit run already knows this path.", C.DIM, colorize))


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


def command_exists_any(names: tuple[str, ...]) -> bool:
    for name in names:
        if command_exists(name):
            return True
        for directory in go_bin_dirs():
            for executable_name in executable_names(name):
                candidate = directory / executable_name
                if candidate.exists() and (is_windows() or os.access(candidate, os.X_OK)):
                    return True
    return False


def tool_exists(tool: str) -> bool:
    return command_exists_any(TOOL_ALIASES.get(tool, (tool,)))


def selected_tools(include_optional: bool) -> list[str]:
    tools = list(REQUIRED_TOOLS) + (list(OPTIONAL_TOOLS) if include_optional else [])
    if is_windows():
        # ReconKit has Python fallbacks for DNS basics on Windows, so BIND-style
        # Unix tools are useful but should not make the installer fail.
        for tool in ("dig", "host"):
            if tool in tools:
                tools.remove(tool)
                if include_optional:
                    tools.append(tool)
    return list(dict.fromkeys(tools))


def required_tools_for_platform() -> tuple[str, ...]:
    if is_windows():
        return tuple(tool for tool in REQUIRED_TOOLS if tool not in {"dig", "host"})
    return REQUIRED_TOOLS


def dependency_rows() -> list[list[str]]:
    rows = []
    platform_required = set(required_tools_for_platform())
    for tool in REQUIRED_TOOLS + OPTIONAL_TOOLS:
        status_text = "found" if tool_exists(tool) else "missing"
        kind = "required" if tool in platform_required else "optional"
        rows.append([tool, kind, status_text])
    return rows


def print_dependencies(*, colorize: bool = True) -> None:
    for directory in go_bin_dirs():
        if directory.expanduser().exists():
            add_to_current_path(directory)
    rows = []
    for tool, kind, status_text in dependency_rows():
        status_color = C.GREEN if status_text == "found" else C.YELLOW
        rows.append([tool, kind, color(status_text, status_color, colorize)])
    print(hr("Dependencies", colorize=colorize))
    print(table(["Tool", "Type", "Status"], rows, colorize=colorize, max_widths=[18, 10, 10]))
    managers = ", ".join(available_managers()) or "none"
    print(color(f"\n[*] Detected installers: {managers}", C.CYAN, colorize))


def native_plan_for(tool: str, kind: str, managers: list[str]) -> InstallPlan | None:
    for manager in managers:
        package = NATIVE_PACKAGES.get(manager, {}).get(tool)
        if package:
            command = install_one_command(manager, package)
            if command:
                return InstallPlan(tool, kind, manager, command)
    return None


def fallback_plan_for(tool: str, kind: str) -> InstallPlan | None:
    if tool in GO_INSTALLS:
        if command_exists("go"):
            return InstallPlan(tool, kind, "go", ["go", "install", GO_INSTALLS[tool]], "Ensure GOPATH/bin or ~/go/bin is in PATH after install.")
        managers = available_managers()
        for manager in managers:
            package = GO_BOOTSTRAP_PACKAGES.get(manager)
            if package:
                command = install_one_command(manager, package)
                if command:
                    return InstallPlan(tool, kind, f"{manager}+go", command, "Installs Go first; re-run --install-deps --with-optional after Go is installed.")
    if tool in PIPX_INSTALLS and command_exists("pipx"):
        return InstallPlan(tool, kind, "pipx", ["pipx", "install", PIPX_INSTALLS[tool]])
    if tool in PIPX_INSTALLS and command_exists("python3"):
        return InstallPlan(tool, kind, "pip", ["python3", "-m", "pip", "install", "--user", PIPX_INSTALLS[tool]], "pipx is preferred when available.")
    if tool in PIPX_INSTALLS and command_exists("py"):
        return InstallPlan(tool, kind, "pip", ["py", "-3", "-m", "pip", "install", "--user", PIPX_INSTALLS[tool]], "Windows Python launcher fallback.")
    if tool in PIPX_INSTALLS and command_exists("python"):
        return InstallPlan(tool, kind, "pip", ["python", "-m", "pip", "install", "--user", PIPX_INSTALLS[tool]], "Python pip fallback.")
    return None


def build_install_plans(missing_tools: list[str]) -> tuple[list[InstallPlan], list[tuple[str, str]]]:
    managers = available_managers()
    plans: list[InstallPlan] = []
    manual: list[tuple[str, str]] = []
    planned_commands: set[tuple[str, ...]] = set()
    for tool in missing_tools:
        kind = "required" if tool in required_tools_for_platform() else "optional"
        plan = native_plan_for(tool, kind, managers) or fallback_plan_for(tool, kind)
        if plan:
            command_key = tuple(plan.command)
            if command_key in planned_commands:
                continue
            planned_commands.add(command_key)
            plans.append(plan)
        else:
            manual.append((tool, MANUAL_HINTS.get(tool, "No automatic installer mapping found for this OS. Install from the upstream project.")))
    return plans, manual


def print_plan(plans: list[InstallPlan], manual: list[tuple[str, str]], *, colorize: bool = True) -> None:
    if plans:
        rows = [[plan.tool, plan.kind, plan.provider, " ".join(plan.command), plan.note] for plan in plans]
        print(hr("Install Plan", colorize=colorize))
        print(table(["Tool", "Type", "Provider", "Command", "Note"], rows, colorize=colorize, max_widths=[16, 10, 10, 78, 48]))
    if manual:
        rows = [[tool, hint] for tool, hint in manual]
        print(hr("Manual Install Notes", colorize=colorize))
        print(table(["Tool", "Install Hint"], rows, colorize=colorize, max_widths=[16, 110]))


def run_install_plan(plans: list[InstallPlan], *, colorize: bool = True) -> list[str]:
    failures: list[str] = []
    updated: set[str] = set()
    for plan in plans:
        if tool_exists(plan.tool):
            continue
        update_cmd = provider_update_command(plan.provider)
        if update_cmd and plan.provider not in updated:
            print(color(f"\n[*] Updating {plan.provider} package metadata...", C.CYAN, colorize))
            update = subprocess.run(update_cmd, check=False)
            updated.add(plan.provider)
            if update.returncode != 0:
                print(color(f"[!] Update failed for {plan.provider}; continuing best-effort.", C.YELLOW, colorize), file=sys.stderr)
        print(color(f"\n[*] Installing {plan.tool} via {plan.provider}...", C.CYAN, colorize))
        result = subprocess.run(plan.command, check=False)
        if result.returncode != 0:
            fallback = fallback_plan_for(plan.tool, plan.kind) if plan.provider not in {"go", "pipx", "pip"} else None
            if fallback and fallback.command != plan.command:
                print(color(f"[!] {plan.provider} install failed for {plan.tool}; trying {fallback.provider} fallback.", C.YELLOW, colorize), file=sys.stderr)
                fallback_result = subprocess.run(fallback.command, check=False)
                if fallback_result.returncode == 0:
                    continue
            failures.append(plan.tool)
            level = C.RED if plan.kind == "required" else C.YELLOW
            print(color(f"[!] Install failed for {plan.tool}; continuing best-effort.", level, colorize), file=sys.stderr)
    return failures


def install_deps(include_optional: bool, dry_run: bool, *, colorize: bool = True) -> int:
    tools = selected_tools(include_optional)
    missing_tools = [tool for tool in tools if not tool_exists(tool)]

    print_dependencies(colorize=colorize)
    if not missing_tools:
        ensure_path_persisted(go_bin_dirs(), dry_run=dry_run, colorize=colorize)
        print(color("\n[+] All selected tools are already installed.", C.GREEN, colorize))
        return 0

    print(color(f"\n[*] Platform: {platform.system()} {platform.release()}", C.CYAN, colorize))
    print(color(f"[*] Missing selected tools: {', '.join(missing_tools)}", C.YELLOW, colorize))

    all_failures: list[str] = []
    all_manual: list[tuple[str, str]] = []
    max_passes = 2
    for pass_index in range(1, max_passes + 1):
        missing_tools = [tool for tool in tools if not tool_exists(tool)]
        if not missing_tools:
            break
        plans, manual = build_install_plans(missing_tools)
        all_manual = manual
        if pass_index == 1 or plans:
            if pass_index > 1:
                print(color(f"\n[*] Continuing dependency install pass {pass_index} after PATH/toolchain refresh...", C.CYAN, colorize))
            print_plan(plans, manual, colorize=colorize)
        ensure_path_persisted(go_bin_dirs(), dry_run=dry_run, colorize=colorize)
        if dry_run:
            if pass_index == 1:
                print(color("\n[+] Dry run only. Re-run without --dry-run to install what can be installed automatically.", C.GREEN, colorize))
            return 0
        if not plans:
            break
        failures = run_install_plan(plans, colorize=colorize)
        all_failures.extend(failures)
        ensure_path_persisted(go_bin_dirs(), dry_run=False, colorize=colorize)

    print(color("\n[+] Installation pass finished. Final status:", C.GREEN, colorize))
    print_dependencies(colorize=colorize)

    remaining_required = [tool for tool in required_tools_for_platform() if not tool_exists(tool)]
    if remaining_required:
        print(color(f"\n[!] Required tools still missing: {', '.join(remaining_required)}", C.RED, colorize), file=sys.stderr)
        return 1

    remaining_optional = [tool for tool in OPTIONAL_TOOLS if include_optional and not tool_exists(tool)]
    if remaining_optional:
        print(color(f"\n[!] Optional tools still missing: {', '.join(remaining_optional)}", C.YELLOW, colorize), file=sys.stderr)
        if all_manual:
            print_plan([], all_manual, colorize=colorize)
    elif include_optional:
        print(color("\n[+] All optional tools are installed or reachable by ReconKit.", C.GREEN, colorize))

    if all_failures:
        print(color(f"\n[!] Some install attempts failed/skipped: {', '.join(sorted(set(all_failures)))}", C.YELLOW, colorize), file=sys.stderr)
    return 0

