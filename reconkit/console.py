import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .constants import AUTHOR, TELEGRAM, VERSION, WEBSITE
from .deps import print_dependencies
from .ui import C, box, color, hr, pill, table


@dataclass
class ConsoleState:
    target: str = ""
    mode: str = "fast"
    modules: str = "safe"
    ports: str = ""
    timeout: int = 90
    raw_dir: str = "artifacts"
    json_out: str = "scan.json"
    markdown_out: str = ""
    html_out: str = ""
    ai: bool = False
    aggressive: bool = False
    no_whois: bool = False
    show_commands: bool = False
    extra: list[str] = field(default_factory=list)


HELP_ROWS = [
    ["help / ?", "Show console commands."],
    ["version", "Show ReconKit version and Team CynetX links."],
    ["show options", "Show current scan settings."],
    ["show modules", "Show module presets and examples."],
    ["show deps", "Check installed tools."],
    ["show ai", "Show AI endpoint/model/config safely."],
    ["ai set model openrouter/free", "Set and save an AI config value."],
    ["ai set-file system_prompt prompt.txt", "Load a config value from a file."],
    ["set target example.com", "Set the target domain/IP/URL."],
    ["set mode fast|balanced|deep", "Choose nmap scan profile."],
    ["set modules safe|all|mission", "Choose extra ReconKit modules."],
    ["set ports 80,443,8080", "Set custom ports; use unset ports to clear."],
    ["enable ai", "Enable AI analysis for the next run."],
    ["disable ai", "Disable AI analysis."],
    ["run", "Run scan with current settings."],
    ["quick example.com", "Fast safe scan immediately."],
    ["mission example.com", "Full mission scan with reports/artifacts."],
    ["install", "Install required + optional tools best-effort."],
    ["uninstall", "Remove the reconkit command launcher."],
    ["uninstall purge", "Remove command plus local ReconKit config/install directory."],
    ["test ai", "Test configured AI endpoint/API key."],
    ["shell <command>", "Run a local shell command."],
    ["exit / quit", "Leave the console."],
]

MODULE_ROWS = [
    ["safe", "DNS tools + web fingerprint + TLS checks."],
    ["all", "safe + passive discovery + DNS AXFR validation + HTTP detail."],
    ["mission", "all + screenshots + nuclei templates when installed."],
    ["none", "Core DNS + nmap only."],
    ["custom", "dns,dns-deep,passive,web,http,tls,screenshots,templates"],
]


def banner(colorize: bool = True) -> str:
    art = r"""
       ____                 __ __ _ __       Console
      / __ \___  _________ / //_(_) /_
     / /_/ / _ \/ ___/ __ \/ ,< / / __/
    / _, _/  __/ /__/ /_/ / /| / / /_
   /_/ |_|\___/\___/\____/_/ |_/_/\__/
    """.strip("\n")
    return color(art, C.BOLD + C.MAGENTA, colorize)


def welcome(state: ConsoleState, *, colorize: bool = True) -> str:
    lines = [
        color(f"⚡ authorized recon console by {AUTHOR}", C.BOLD + C.CYAN, colorize),
        pill("TARGET", state.target or "not set", C.YELLOW, colorize=colorize),
        pill("MODE", state.mode, C.MAGENTA, colorize=colorize),
        pill("MODULES", state.modules, C.GREEN, colorize=colorize),
        pill("TEAM", "cynetx.ir • t.me/cynetx", C.CYAN, colorize=colorize),
        "Type " + color("help", C.BOLD + C.WHITE, colorize) + " for commands, " + color("run", C.BOLD + C.WHITE, colorize) + " to scan, " + color("exit", C.BOLD + C.WHITE, colorize) + " to quit.",
    ]
    return "\n".join([banner(colorize), box(lines, title=" ReconKit Console ", accent=C.MAGENTA, colorize=colorize)])


def options_rows(state: ConsoleState) -> list[list[str]]:
    return [
        ["target", state.target or "<required>"],
        ["mode", state.mode],
        ["modules", state.modules],
        ["ports", state.ports or "default"],
        ["timeout", str(state.timeout)],
        ["raw_dir", state.raw_dir or "disabled"],
        ["json", state.json_out or "disabled"],
        ["markdown", state.markdown_out or "disabled"],
        ["html", state.html_out or "disabled"],
        ["ai", "on" if state.ai else "off"],
        ["aggressive", "on" if state.aggressive else "off"],
        ["no_whois", "on" if state.no_whois else "off"],
        ["show_commands", "on" if state.show_commands else "off"],
        ["extra", " ".join(state.extra) if state.extra else "none"],
    ]


def build_scan_args(state: ConsoleState) -> list[str]:
    if not state.target:
        raise ValueError("target is not set. Use: set target example.com")
    args = [state.target, "-m", state.mode, "-M", state.modules, "-t", str(state.timeout)]
    if state.ports:
        args.extend(["-p", state.ports])
    if state.aggressive:
        args.append("-A")
    if state.no_whois:
        args.append("--no-whois")
    if state.show_commands:
        args.append("--cmd")
    if state.raw_dir:
        args.extend(["--raw-dir", state.raw_dir])
    if state.json_out:
        args.extend(["-o", state.json_out])
    if state.markdown_out:
        args.extend(["--markdown", state.markdown_out])
    if state.html_out:
        args.extend(["--html", state.html_out])
    if state.ai:
        args.append("--ai")
    args.extend(state.extra)
    return args


def print_help(*, colorize: bool = True) -> None:
    print(hr("Console Commands", colorize=colorize))
    print(table(["Command", "Meaning"], HELP_ROWS, colorize=colorize, max_widths=[30, 90]))


def set_option(state: ConsoleState, key: str, value: str) -> None:
    normalized = key.replace("-", "_").lower()
    if normalized in {"target", "rhost", "rhosts"}:
        state.target = value
    elif normalized in {"mode", "profile"}:
        if value not in {"fast", "balanced", "deep"}:
            raise ValueError("mode must be fast, balanced, or deep")
        state.mode = value
    elif normalized in {"modules", "module"}:
        state.modules = value
    elif normalized in {"ports", "port"}:
        state.ports = value
    elif normalized == "timeout":
        state.timeout = int(value)
    elif normalized in {"raw_dir", "raw"}:
        state.raw_dir = value
    elif normalized in {"json", "json_out"}:
        state.json_out = value
    elif normalized in {"markdown", "md"}:
        state.markdown_out = value
    elif normalized == "html":
        state.html_out = value
    elif normalized == "extra":
        state.extra = shlex.split(value)
    else:
        raise ValueError(f"unknown option: {key}")


def unset_option(state: ConsoleState, key: str) -> None:
    normalized = key.replace("-", "_").lower()
    if normalized == "ports":
        state.ports = ""
    elif normalized == "raw_dir":
        state.raw_dir = ""
    elif normalized in {"json", "json_out"}:
        state.json_out = ""
    elif normalized in {"markdown", "md"}:
        state.markdown_out = ""
    elif normalized == "html":
        state.html_out = ""
    elif normalized == "extra":
        state.extra = []
    else:
        raise ValueError(f"cannot unset option: {key}")


def run_main(args: list[str]) -> int:
    from .cli import main

    return main(args)


def handle_command(line: str, state: ConsoleState, *, colorize: bool = True) -> bool:
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        print(color(f"[!] Parse error: {exc}", C.RED, colorize))
        return True
    if not parts:
        return True

    command = parts[0].lower()
    rest = parts[1:]

    try:
        if command == "version":
            print(color(f"ReconKit v{VERSION} by {AUTHOR}", C.BOLD + C.CYAN, colorize))
            print(f"Website: {WEBSITE}")
            print(f"Telegram: {TELEGRAM}")
        elif command in {"exit", "quit", "q"}:
            print(color("[+] leaving ReconKit console", C.GREEN, colorize))
            return False
        if command in {"help", "?"}:
            print_help(colorize=colorize)
        elif command == "show" and rest[:1] == ["options"]:
            print(hr("Current Options", colorize=colorize))
            print(table(["Option", "Value"], options_rows(state), colorize=colorize, max_widths=[18, 104]))
        elif command == "show" and rest[:1] == ["modules"]:
            print(hr("Module Presets", colorize=colorize))
            print(table(["Module", "What it runs"], MODULE_ROWS, colorize=colorize, max_widths=[16, 104]))
        elif command == "show" and rest[:1] in (["deps"], ["tools"]):
            print_dependencies(colorize=colorize)
        elif command == "show" and rest[:1] == ["ai"]:
            run_main(["--ai-show"])
        elif command == "ai" and rest[:1] == ["init"]:
            run_main(["--ai-init"])
        elif command == "ai" and rest[:1] == ["prompt"]:
            run_main(["--ai-prompt"])
        elif command == "ai" and rest[:1] == ["show"]:
            run_main(["--ai-show"])
        elif command == "ai" and len(rest) >= 3 and rest[0] == "set":
            key = rest[1]
            value = " ".join(rest[2:])
            run_main(["--ai-set", f"{key}={value}"])
        elif command == "ai" and len(rest) == 3 and rest[0] in {"set-file", "file"}:
            run_main(["--ai-set-file", f"{rest[1]}={rest[2]}"])
        elif command == "set" and len(rest) >= 2:
            key = rest[0]
            value = " ".join(rest[1:])
            set_option(state, key, value)
            print(color(f"[+] {key} => {value}", C.GREEN, colorize))
        elif command == "unset" and len(rest) == 1:
            unset_option(state, rest[0])
            print(color(f"[+] unset {rest[0]}", C.GREEN, colorize))
        elif command == "enable" and rest:
            flag = rest[0].replace("-", "_").lower()
            if flag in {"ai", "aggressive", "no_whois", "show_commands"}:
                setattr(state, flag, True)
                print(color(f"[+] enabled {flag}", C.GREEN, colorize))
            else:
                raise ValueError(f"unknown flag: {rest[0]}")
        elif command == "disable" and rest:
            flag = rest[0].replace("-", "_").lower()
            if flag in {"ai", "aggressive", "no_whois", "show_commands"}:
                setattr(state, flag, False)
                print(color(f"[+] disabled {flag}", C.GREEN, colorize))
            else:
                raise ValueError(f"unknown flag: {rest[0]}")
        elif command in {"run", "scan"}:
            args = build_scan_args(state)
            print(color("[◆] reconkit " + " ".join(shlex.quote(item) for item in args), C.CYAN, colorize))
            run_main(args)
        elif command == "quick" and rest:
            state.target = rest[0]
            state.mode = "fast"
            state.modules = "safe"
            run_main(build_scan_args(state))
        elif command == "mission" and rest:
            state.target = rest[0]
            state.mode = "balanced"
            state.modules = "mission"
            state.raw_dir = state.raw_dir or "artifacts"
            state.json_out = state.json_out or "scan.json"
            state.html_out = state.html_out or "report.html"
            run_main(build_scan_args(state))
        elif command == "install":
            run_main(["--install-deps", "--with-optional"])
        elif command == "uninstall":
            uninstall_args = ["--uninstall"]
            if rest[:1] == ["purge"]:
                uninstall_args.append("--purge")
            elif rest[:1] == ["dryrun"]:
                uninstall_args.append("--dry-run")
            run_main(uninstall_args)
        elif command == "dryrun":
            run_main(["--install-deps", "--with-optional", "--dry-run"])
        elif command == "test" and rest[:1] == ["ai"]:
            run_main(["--test-ai"])
        elif command == "clear":
            print("\033c", end="")
            print(welcome(state, colorize=colorize))
        elif command == "shell" and rest:
            import subprocess

            subprocess.run(" ".join(shlex.quote(item) for item in rest), shell=True, check=False)
        else:
            print(color("[!] Unknown command. Type: help", C.YELLOW, colorize))
    except (ValueError, OSError) as exc:
        print(color(f"[!] {exc}", C.RED, colorize))
    except KeyboardInterrupt:
        print(color("\n[!] interrupted", C.YELLOW, colorize))
    return True


def run_console(*, colorize: bool = True) -> int:
    state = ConsoleState()
    print(welcome(state, colorize=colorize))
    while True:
        try:
            prompt_target = state.target or "no-target"
            line = input(color(f"reconkit({prompt_target})> ", C.BOLD + C.CYAN, colorize))
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print(color("\n[!] Type exit to quit.", C.YELLOW, colorize))
            continue
        if not handle_command(line, state, colorize=colorize):
            return 0
