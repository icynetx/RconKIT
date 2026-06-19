import html
import json
from pathlib import Path

from .constants import AUTHOR, COPYRIGHT, TELEGRAM, WEBSITE
from .models import ReconReport


def report_dict(report: ReconReport) -> dict[str, object]:
    data = report.__dict__.copy()
    data["generated_by"] = {"name": "ReconKit", "author": AUTHOR, "website": WEBSITE, "telegram": TELEGRAM, "copyright": COPYRIGHT}
    data["extras"] = [extra.__dict__ for extra in report.extras]
    data["findings"] = [finding.__dict__ for finding in report.findings]
    return data


def save_json(report: ReconReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_dict(report), indent=2, ensure_ascii=False), encoding="utf-8")


def markdown_report(report: ReconReport) -> str:
    open_ports = [item for item in report.nmap_ports if item.get("state") == "open"]
    lines = [
        f"# ReconKit Report: `{report.normalized_target}`",
        f"Built by **{AUTHOR}** · {WEBSITE} · {TELEGRAM}",
        "",
        "## Mission Summary",
        f"- Started: `{report.started_at}`",
        f"- Profile: `{report.profile}`",
        f"- Resolved IPs: `{', '.join(report.resolved_ips) if report.resolved_ips else 'none'}`",
        f"- Open ports: `{', '.join(item['port'] for item in open_ports) if open_ports else 'none'}`",
        f"- Extra tools: `{len(report.extras)}`",
        "",
        "## Ports & Services",
        "| Port | State | Service | Version |",
        "|---|---|---|---|",
    ]
    for item in report.nmap_ports:
        lines.append(f"| `{item.get('port','')}` | {item.get('state','')} | {item.get('service','')} | {item.get('version','')} |")
    lines.extend(["", "## DNS Records", "| Type | Value |", "|---|---|"])
    for record, values in report.dns_records.items():
        for value in values:
            lines.append(f"| {record} | `{value}` |")
    lines.extend(["", "## Extra Tooling", "| Module | Tool | Status | Summary |", "|---|---|---|---|"])
    for extra in report.extras:
        status = "missing" if extra.missing else ("ok" if extra.ok else "warn")
        summary = "<br>".join(extra.summary) if extra.summary else "no output"
        lines.append(f"| {extra.module} | {extra.tool} | {status} | {summary} |")
    if report.notes:
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in sorted(set(report.notes)))
    if report.artifacts:
        lines.extend(["", "## Artifacts"])
        lines.extend(f"- `{name}`: `{path}`" for name, path in sorted(report.artifacts.items()))
    return "\n".join(lines) + "\n"


def save_markdown(report: ReconReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_report(report), encoding="utf-8")


def save_html(report: ReconReport, path: Path) -> None:
    markdown = markdown_report(report)
    body = "\n".join(
        f"<p>{html.escape(line)}</p>" if line and not line.startswith("#") else f"<h2>{html.escape(line.lstrip('# ').strip())}</h2>"
        for line in markdown.splitlines()
    )
    document = f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>ReconKit Report - {html.escape(report.normalized_target)}</title>
<style>
body{{background:#0b1020;color:#d9e7ff;font-family:Inter,Segoe UI,Arial,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.5}}
h1,h2{{color:#66e3ff}} p{{background:#111936;border:1px solid #26345f;border-radius:10px;padding:10px 12px;white-space:pre-wrap}}
code{{color:#9dffb0}} a{{color:#66e3ff}}
</style>
</head>
<body>
<h1>ReconKit Report</h1>
{body}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")


def diff_reports(old_path: Path, new_report: ReconReport) -> list[str]:
    old = json.loads(old_path.read_text(encoding="utf-8"))
    old_ports = {item.get("port") for item in old.get("nmap_ports", []) if item.get("state") == "open"}
    new_ports = {item.get("port") for item in new_report.nmap_ports if item.get("state") == "open"}
    old_ips = set(old.get("resolved_ips", []))
    new_ips = set(new_report.resolved_ips)
    lines = []
    for port in sorted(new_ports - old_ports):
        lines.append(f"New open port: {port}")
    for port in sorted(old_ports - new_ports):
        lines.append(f"Closed/missing port: {port}")
    for ip in sorted(new_ips - old_ips):
        lines.append(f"New resolved IP: {ip}")
    for ip in sorted(old_ips - new_ips):
        lines.append(f"Removed resolved IP: {ip}")
    return lines or ["No high-level port/IP changes detected."]
