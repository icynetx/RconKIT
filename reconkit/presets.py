import json
import re
import shlex
from pathlib import Path

from .constants import PRESETS_PATH

BUILTIN_PRESET_NAMES = ("quick", "standard", "full", "web", "vuln")
PRESET_TOOLS = (
    "nmap", "dig", "host", "nslookup", "whois", "whatweb", "httpx", "wafw00f", "nikto",
    "sslscan", "testssl.sh", "subfinder", "amass", "curl", "katana", "gowitness", "nuclei",
)
BLOCKED_ARGS = {
    "nmap": {"-D", "--decoy", "--spoof-mac", "--badsum", "-f", "--mtu", "-g", "--source-port"},
}


def load_presets(path: Path = PRESETS_PATH) -> dict[str, object]:
    if not path.exists():
        return {"presets": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid preset file {path}: root must be an object")
    presets = data.get("presets", {})
    if not isinstance(presets, dict):
        raise ValueError(f"Invalid preset file {path}: presets must be an object")
    return {"presets": presets}


def save_presets(data: dict[str, object], path: Path = PRESETS_PATH) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_preset_name(name: str) -> str:
    clean = name.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,48}", clean):
        raise ValueError("Preset name must be 1-48 chars: letters, numbers, dot, dash, underscore")
    return clean


def split_args(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    return shlex.split(raw)


def validate_tool_args(tool: str, args: list[str]) -> None:
    blocked = BLOCKED_ARGS.get(tool, set())
    for arg in args:
        if arg in blocked:
            raise ValueError(f"Argument {arg!r} is not allowed in ReconKit presets for {tool}")
        if any(arg.startswith(blocked_arg + "=") for blocked_arg in blocked if blocked_arg.startswith("--")):
            raise ValueError(f"Argument {arg!r} is not allowed in ReconKit presets for {tool}")


def normalize_tool_args(tool_args: dict[str, list[str] | str]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for tool, value in tool_args.items():
        if tool not in PRESET_TOOLS:
            raise ValueError(f"Unknown tool in preset: {tool}")
        args = split_args(value) if isinstance(value, str) else list(value)
        validate_tool_args(tool, args)
        if args:
            normalized[tool] = args
    return normalized


def get_custom_preset(name: str) -> dict[str, object] | None:
    data = load_presets()
    preset = data.get("presets", {}).get(name)
    return preset if isinstance(preset, dict) else None


def preset_exists(name: str) -> bool:
    return name in BUILTIN_PRESET_NAMES or get_custom_preset(name) is not None


def preset_base(name: str) -> str:
    preset = get_custom_preset(name)
    if preset:
        base = str(preset.get("base", "standard"))
        return base if base in BUILTIN_PRESET_NAMES else "standard"
    return name if name in BUILTIN_PRESET_NAMES else "standard"


def preset_tool_args(name: str, tool: str) -> list[str]:
    preset = get_custom_preset(name)
    if not preset:
        return []
    tool_args = preset.get("tool_args", {})
    if not isinstance(tool_args, dict):
        return []
    args = tool_args.get(tool, [])
    if not isinstance(args, list):
        return []
    return [str(item) for item in args]


def create_preset(name: str, base: str, tool_args: dict[str, list[str] | str], description: str = "") -> dict[str, object]:
    clean = validate_preset_name(name)
    if clean in BUILTIN_PRESET_NAMES:
        raise ValueError(f"Cannot overwrite built-in preset: {clean}")
    if base not in BUILTIN_PRESET_NAMES:
        raise ValueError(f"Base preset must be one of: {', '.join(BUILTIN_PRESET_NAMES)}")
    normalized = normalize_tool_args(tool_args)
    data = load_presets()
    presets = data.setdefault("presets", {})
    if not isinstance(presets, dict):
        raise ValueError("Invalid preset storage")
    presets[clean] = {"base": base, "description": description.strip(), "tool_args": normalized}
    save_presets(data)
    return presets[clean]


def delete_preset(name: str) -> bool:
    clean = validate_preset_name(name)
    if clean in BUILTIN_PRESET_NAMES:
        raise ValueError("Built-in presets cannot be deleted")
    data = load_presets()
    presets = data.get("presets", {})
    if not isinstance(presets, dict) or clean not in presets:
        return False
    del presets[clean]
    save_presets(data)
    return True


def list_preset_rows() -> list[list[str]]:
    rows = [[name, "built-in", name, "ReconKit built-in scan preset"] for name in BUILTIN_PRESET_NAMES]
    data = load_presets()
    presets = data.get("presets", {})
    if isinstance(presets, dict):
        for name, preset in sorted(presets.items()):
            if isinstance(preset, dict):
                rows.append([name, "custom", str(preset.get("base", "standard")), str(preset.get("description", ""))])
    return rows


def prompt_create_preset(name: str, base: str = "standard") -> dict[str, object]:
    print(f"[+] Creating preset: {name}")
    print(f"[*] Base preset: {base}")
    description = input("Description (optional): ").strip()
    print("\nEnter extra arguments for each tool. Leave blank to skip.")
    print("Example: nmap => --reason --top-ports 1000")
    print("Tip: arguments are appended to ReconKit's safe default command for that tool.\n")
    tool_args: dict[str, list[str]] = {}
    for tool in PRESET_TOOLS:
        while True:
            raw = input(f"{tool} args: ").strip()
            try:
                args = split_args(raw)
                validate_tool_args(tool, args)
                break
            except ValueError as exc:
                print(f"[!] {exc}")
        if args:
            tool_args[tool] = args
    return create_preset(name, base, tool_args, description)
