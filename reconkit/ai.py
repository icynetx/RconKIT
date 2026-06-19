import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .constants import CONFIG_PATH, DEFAULT_AI_CONFIG
from .models import ReconReport
from .ui import hr

def load_config(path: Path = CONFIG_PATH) -> dict[str, object]:
    config = dict(DEFAULT_AI_CONFIG)
    if not path.exists():
        return config
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid config {path}: root must be a JSON object")
    ai_config = loaded.get("ai", loaded)
    if not isinstance(ai_config, dict):
        raise ValueError(f"Invalid config {path}: ai must be a JSON object")
    for key, value in ai_config.items():
        if key in config:
            config[key] = value
    return config


def parse_ai_config_value(key: str, value: str) -> object:
    if key not in DEFAULT_AI_CONFIG:
        allowed = ", ".join(sorted(DEFAULT_AI_CONFIG))
        raise ValueError(f"Unknown AI config key: {key}. Allowed keys: {allowed}")
    default = DEFAULT_AI_CONFIG[key]
    if isinstance(default, bool):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"AI config key {key} expects a boolean value")
    if isinstance(default, int) and not isinstance(default, bool):
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"AI config key {key} expects an integer") from exc
    if isinstance(default, float):
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"AI config key {key} expects a number") from exc
    return value


def apply_ai_config_updates(
    config: dict[str, object],
    assignments: list[str] | None = None,
    file_assignments: list[str] | None = None,
) -> dict[str, object]:
    updated = dict(config)
    for assignment in assignments or []:
        if "=" not in assignment:
            raise ValueError(f"Invalid --ai-set value: {assignment}. Use KEY=VALUE")
        key, value = assignment.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Invalid --ai-set value: key is empty")
        updated[key] = parse_ai_config_value(key, value)
    for assignment in file_assignments or []:
        if "=" not in assignment:
            raise ValueError(f"Invalid --ai-set-file value: {assignment}. Use KEY=PATH")
        key, file_path = assignment.split("=", 1)
        key = key.strip()
        if key not in DEFAULT_AI_CONFIG:
            allowed = ", ".join(sorted(DEFAULT_AI_CONFIG))
            raise ValueError(f"Unknown AI config key: {key}. Allowed keys: {allowed}")
        path = Path(file_path).expanduser()
        updated[key] = path.read_text(encoding="utf-8").strip()
    return updated


def save_config(config: dict[str, object], path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {key: config.get(key, DEFAULT_AI_CONFIG[key]) for key in DEFAULT_AI_CONFIG}
    path.write_text(json.dumps({"ai": ordered}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def validate_ai_config(config: dict[str, object]) -> None:
    required = ("endpoint_url", "model", "system_prompt", "api_key_env")
    for key in required:
        if not str(config.get(key, "")).strip():
            raise ValueError(f"AI config missing required key: {key}")
    try:
        float(config.get("temperature", 0.2))
        int(config.get("max_tokens", 1600))
        int(config.get("continuation_rounds", 3))
        int(config.get("empty_response_retries", 3))
        float(config.get("retry_delay_seconds", 2))
    except (TypeError, ValueError) as exc:
        raise ValueError("AI config temperature/max_tokens/continuation/retry values must be numeric") from exc

def looks_like_secret(value: object) -> bool:
    text = str(value or "")
    return text.startswith(("sk-", "sk_or_", "sk-or-")) or len(text) > 48 and " " not in text

def masked_secret(value: object) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 10:
        return "***"
    return text[:6] + "..." + text[-4:]

def safe_config_for_display(config: dict[str, object]) -> dict[str, object]:
    safe = dict(config)
    if safe.get("api_key"):
        safe["api_key"] = masked_secret(safe["api_key"])
    if looks_like_secret(safe.get("api_key_env")):
        safe["api_key_env"] = masked_secret(safe["api_key_env"])
        safe["api_key_env_note"] = "This looks like a direct key; prefer api_key or OPENROUTER_API_KEY env var."
    return safe

def ai_api_key(config: dict[str, object]) -> str | None:
    direct_key = str(config.get("api_key", "") or "").strip()
    if direct_key:
        return direct_key
    env_name = str(config.get("api_key_env", "OPENROUTER_API_KEY") or "OPENROUTER_API_KEY").strip()
    if looks_like_secret(env_name):
        return env_name
    return os.environ.get(env_name)

def ai_key_hint(config: dict[str, object]) -> str:
    env_name = str(config.get("api_key_env", "OPENROUTER_API_KEY") or "OPENROUTER_API_KEY").strip()
    if looks_like_secret(env_name):
        return "Move your key to ai.api_key or set OPENROUTER_API_KEY; do not put raw keys in api_key_env."
    return f"Set {env_name} in your environment or ai.api_key in recon_config.json."

def report_for_ai(report: ReconReport) -> dict[str, object]:
    return {
        "target": report.normalized_target,
        "started_at": report.started_at,
        "elapsed_seconds": round(report.elapsed_seconds, 2),
        "mode": report.profile,
        "resolved_ips": report.resolved_ips,
        "reverse_dns": report.reverse_dns,
        "dns_records": report.dns_records,
        "ports": report.nmap_ports,
        "whois_summary": report.whois_summary[:12],
        "extra_tools": [
            {
                "module": extra.module,
                "tool": extra.tool,
                "ok": extra.ok,
                "missing": extra.missing,
                "summary": extra.summary[:8],
            }
            for extra in report.extras
        ],
        "notes": sorted(set(report.notes)),
        "commands": [
            {"command": item.get("command"), "ok": item.get("ok"), "elapsed_seconds": item.get("elapsed_seconds")}
            for item in report.commands
        ],
    }

def build_ai_user_prompt(report: ReconReport) -> str:
    payload = json.dumps(report_for_ai(report), ensure_ascii=False, indent=2)
    return (
        "This is an authorized ReconKit scan summary. Analyze it exactly according to the configured system prompt. "
        "Use only the JSON data below. If evidence is missing or uncertain, say so clearly.\n\n"
        f"```json\n{payload}\n```"
    )

def extract_ai_content(parsed: dict[str, object]) -> tuple[str, str | None, str]:
    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter response did not include choices")
    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    content_text = "" if content is None else str(content).strip()
    finish_reason = choice.get("finish_reason")
    diagnostic = f"finish_reason={finish_reason}"
    provider = (parsed.get("provider") or parsed.get("provider_name") or choice.get("provider"))
    if provider:
        diagnostic += f", provider={provider}"
    if not content_text:
        reasoning = message.get("reasoning") or message.get("reasoning_content") or choice.get("reasoning")
        if reasoning:
            diagnostic += ", reasoning_without_content=true"
    return content_text, finish_reason, diagnostic

def ai_report_quality_issue(text: str) -> str | None:
    plain = text.strip()
    if len(plain) < 500:
        return "AI response was too short to be a useful report"
    required_markers = ("Executive Summary", "Attack Surface", "Risk Assessment", "Recommended Next")
    missing = [marker for marker in required_markers if marker.lower() not in plain.lower()]
    if len(missing) >= 2:
        return "AI response did not follow the required report structure"
    return None

def openrouter_chat(messages: list[dict[str, str]], config: dict[str, object], api_key: str, timeout: int) -> dict[str, object]:
    body = {
        "model": str(config["model"]),
        "messages": messages,
        "temperature": float(config.get("temperature", 0.2)),
        "max_tokens": int(config.get("max_tokens", 3200)),
    }
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        str(config["endpoint_url"]),
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": str(config.get("http_referer", "https://local.reconkit")),
            "X-Title": str(config.get("x_title", "ReconKit AI Analysis")),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(10, timeout)) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenRouter connection failed: {exc.reason}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        preview = raw[:300].replace("\n", " ")
        raise RuntimeError(f"AI response was not JSON. Check endpoint_url/model. Response preview: {preview}") from exc

def call_openrouter(report: ReconReport, config: dict[str, object], api_key: str, timeout: int, *, colorize: bool = True) -> str:
    messages = [
        {"role": "system", "content": str(config["system_prompt"])},
        {"role": "user", "content": build_ai_user_prompt(report)},
    ]
    chunks: list[str] = []
    max_rounds = int(config.get("continuation_rounds", 3))
    empty_retries = max(0, int(config.get("empty_response_retries", 3)))
    retry_delay = max(0.0, float(config.get("retry_delay_seconds", 2)))
    last_empty_diagnostic = ""
    for round_index in range(max(1, max_rounds)):
        content = ""
        finish_reason = None
        for attempt in range(empty_retries + 1):
            parsed = openrouter_chat(messages, config, api_key, timeout)
            content, finish_reason, diagnostic = extract_ai_content(parsed)
            quality_issue = ai_report_quality_issue(content) if content else "empty response"
            if content and not quality_issue:
                break
            last_empty_diagnostic = diagnostic if not content else f"{diagnostic}, quality_issue={quality_issue}"
            content = ""
            if attempt < empty_retries:
                time.sleep(retry_delay)
        if not content:
            raise RuntimeError(
                "OpenRouter returned no usable report after retries. "
                f"Last response: {last_empty_diagnostic}. "
                "With openrouter/free this can happen when the random free model fails; retry or use a fixed free chat model."
            )
        chunks.append(content)
        if finish_reason != "length":
            break
        messages.extend([
            {"role": "assistant", "content": content},
            {
                "role": "user",
                "content": "Continue exactly from where the previous answer stopped. Do not repeat earlier sections. Complete the remaining required report sections in English.",
            },
        ])
    else:
        chunks.append("\n\n[Warning: AI output may still be incomplete after continuation rounds; increase max_tokens or continuation_rounds in recon_config.json.]" )
    return "\n".join(chunks).strip()

def render_ai_analysis(text: str, *, colorize: bool = True) -> str:
    return "\n".join([hr("AI Analysis", colorize=colorize), text])

def test_ai_connection(config: dict[str, object], api_key: str, timeout: int) -> str:
    body = {
        "model": str(config["model"]),
        "messages": [
            {"role": "system", "content": "You are a health-check responder. Reply with exactly: OK"},
            {"role": "user", "content": "Reply with the single word OK. No explanation."},
        ],
        "temperature": 0,
        "max_tokens": 64,
    }
    attempts = max(1, int(config.get("empty_response_retries", 3)) + 1)
    retry_delay = max(0.0, float(config.get("retry_delay_seconds", 2)))
    last_error = ""
    for attempt in range(attempts):
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            str(config["endpoint_url"]),
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": str(config.get("http_referer", "https://local.reconkit")),
                "X-Title": str(config.get("x_title", "ReconKit AI Test")),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=max(10, timeout)) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter connection failed: {exc.reason}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            preview = raw[:300].replace("\n", " ")
            raise RuntimeError(f"AI test response was not JSON. Check endpoint_url/model. Response preview: {preview}") from exc
        choices = parsed.get("choices") or []
        if not choices:
            last_error = "AI test response did not include choices"
        else:
            choice = choices[0]
            message = choice.get("message") or {}
            content, finish_reason, diagnostic = extract_ai_content(parsed)
            content_text = content
            if content_text and content_text.lower() not in {"none", "null"}:
                return content_text
            reasoning = message.get("reasoning") or message.get("reasoning_content") or choice.get("reasoning")
            reasoning_text = "" if reasoning is None else str(reasoning).strip()
            if reasoning_text:
                last_error = (
                    "AI test reached the API, but selected model returned reasoning without final content "
                    f"({diagnostic})."
                )
            else:
                last_error = f"AI test reached the API, but model returned empty content ({diagnostic})."
        if attempt < attempts - 1:
            time.sleep(retry_delay)
    raise RuntimeError(
        f"{last_error} For openrouter/free this can happen randomly after retries; run --test-ai again or use a fixed chat model."
    )

