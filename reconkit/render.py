from .constants import APP, BANNER, DEFAULT_RECORDS, SERVICE_HINTS, VERSION
from .models import ReconReport
from .target import target_has_scan_endpoint
from .ui import C, box, color, hr, pill, table

def port_severity(item: dict[str, str]) -> tuple[str, str]:
    service = item["service"].lower()
    port = item["port"].split("/", 1)[0]
    high = {"21", "23", "445", "3306", "5432", "6379", "3389", "5900", "9200", "9300"}
    medium_services = {"ftp", "smtp", "domain", "mysql", "postgresql", "redis", "ms-wbt-server", "microsoft-ds"}
    if port in high or service in medium_services:
        return "watch", C.YELLOW
    if item["state"] == "open":
        return "open", C.GREEN
    return "info", C.BLUE

def render_banner(report: ReconReport, *, colorize: bool = True) -> str:
    banner = color(BANNER, C.BOLD + C.MAGENTA, colorize)
    open_count = sum(1 for item in report.nmap_ports if item["state"] == "open")
    dns_count = sum(len(values) for values in report.dns_records.values())
    meta = [
        color("⚡ cyber recon dashboard", C.BOLD + C.CYAN, colorize),
        pill("TARGET", report.normalized_target, C.CYAN, colorize=colorize),
        pill("MODE", report.profile, C.MAGENTA, colorize=colorize),
        pill("IPS", str(len(report.resolved_ips)), C.BLUE, colorize=colorize),
        pill("DNS", str(dns_count), C.YELLOW, colorize=colorize),
        pill("OPEN", str(open_count), C.GREEN if open_count else C.DIM, colorize=colorize),
    ]
    return banner + "\n" + box(meta, title=f"{APP} v{VERSION}", accent=C.MAGENTA, colorize=colorize)

def render_summary(report: ReconReport, *, colorize: bool = True) -> str:
    open_ports = [item for item in report.nmap_ports if item["state"] == "open"]
    exposed = ", ".join(item["port"] for item in open_ports) or "none"
    risk = "LOW"
    risk_color = C.GREEN
    if not target_has_scan_endpoint(report):
        risk = "DNS_FAIL"
        risk_color = C.YELLOW
    if any(port_severity(item)[0] == "watch" for item in open_ports):
        risk = "REVIEW"
        risk_color = C.YELLOW
    if len(open_ports) >= 8:
        risk = "BROAD"
        risk_color = C.RED
    rows = [
        ["Target", report.normalized_target],
        ["Started", report.started_at],
        ["Elapsed", f"{report.elapsed_seconds:.1f}s"],
        ["Open ports", exposed],
        ["Extra tools", str(len(report.extras))],
        ["Exposure", color(risk, C.BOLD + risk_color, colorize)],
    ]
    return table(["Signal", "Value"], rows, colorize=colorize, max_widths=[14, 80])

def render_findings(report: ReconReport, *, colorize: bool = True) -> str:
    rows = []
    for item in report.nmap_ports:
        severity, severity_color = port_severity(item)
        service = item["service"].lower()
        hint = SERVICE_HINTS.get(service, "Review service exposure, version, and access controls.")
        rows.append([color(severity.upper(), C.BOLD + severity_color, colorize), item["port"], item["service"], hint])
    return table(["Flag", "Port", "Service", "Why it matters"], rows, colorize=colorize, max_widths=[8, 10, 14, 70])


def render_executive_brief(report: ReconReport, *, colorize: bool = True) -> str:
    open_ports = [item for item in report.nmap_ports if item["state"] == "open"]
    rows = [
        ["Resolution", f"{len(report.resolved_ips)} IP(s): {', '.join(report.resolved_ips) if report.resolved_ips else 'none'}"],
        ["Surface", f"{len(open_ports)} open port(s) detected"],
        ["Web", "yes" if any(item["port"].split("/", 1)[0] in {"80", "443", "2082", "2083", "2095", "2096", "8080", "8443"} for item in open_ports) else "not observed"],
        ["Mail", "yes" if any(item["port"].split("/", 1)[0] in {"25", "465", "587", "110", "143", "993", "995"} for item in open_ports) else "not observed"],
        ["Priority", "Review WATCH/BROAD exposure first" if open_ports else "Fix DNS/target resolution first"],
    ]
    return table(["Signal", "Interpretation"], rows, colorize=colorize, max_widths=[14, 92])


def render_next_steps(report: ReconReport, *, colorize: bool = True) -> str:
    if not target_has_scan_endpoint(report):
        rows = [
            ["Validate DNS", f"dig +short {report.normalized_target} A"],
            ["Check typo", f"host -a {report.normalized_target}"],
        ]
        return table(["Step", "Command"], rows, colorize=colorize, max_widths=[18, 96])

    open_ports = [item["port"].split("/", 1)[0] for item in report.nmap_ports if item["state"] == "open"]
    port_csv = ",".join(open_ports[:25]) or "80,443"
    rows = [
        ["Confirm services", f"nmap -sV --version-light -Pn -p {port_csv} {report.normalized_target}"],
        ["DNS safety", f"dig axfr @{report.resolved_ips[0] if report.resolved_ips else report.normalized_target} {report.normalized_target}"],
    ]
    if any(port in {"80", "443", "2082", "2083", "2095", "2096", "8080", "8443"} for port in open_ports):
        rows.append(["Web headers", f"curl -I https://{report.normalized_target}"])
        rows.append(["Web fingerprint", f"whatweb --no-errors https://{report.normalized_target}"])
    if any(port in {"443", "465", "993", "995", "2083", "2096", "8443"} for port in open_ports):
        rows.append(["TLS review", f"sslscan --no-colour {report.normalized_target}:443"])
    return table(["Step", "Command"], rows, colorize=colorize, max_widths=[18, 96])


def render_commands(report: ReconReport, *, colorize: bool = True) -> str:
    rows = []
    for idx, command in enumerate(report.commands, 1):
        state = "ok" if command["ok"] else "warn"
        state_color = C.GREEN if command["ok"] else C.YELLOW
        rows.append([str(idx), color(state, state_color, colorize), f"{command['elapsed_seconds']}s", str(command["command"])])
    return table(["#", "Status", "Time", "Command"], rows, colorize=colorize, max_widths=[3, 8, 8, 100])

def render_extra_tools(report: ReconReport, *, colorize: bool = True) -> str:
    rows = []
    for extra in report.extras:
        state = "missing" if extra.missing else ("ok" if extra.ok else "warn")
        state_color = C.DIM if extra.missing else (C.GREEN if extra.ok else C.YELLOW)
        summary = " | ".join(extra.summary) if extra.summary else "no output"
        rows.append([extra.module, extra.tool, color(state, state_color, colorize), f"{extra.elapsed:.1f}s", summary])
    return table(["Module", "Tool", "Status", "Time", "Summary"], rows, colorize=colorize, max_widths=[16, 14, 8, 8, 82])

def render_switch_guide(*, colorize: bool = True) -> str:
    rows = [
        ["-m fast", "Quick default: DNS + two-stage nmap on common hosting ports."],
        ["-m balanced", "More ports: adds databases, admin panels, file sharing, infra ports."],
        ["-m deep", "Heavier nmap: -sV -sC top 1000; slower, more detail."],
        ["-p 80,443", "Scan exact ports. Alias for --ports."],
        ["-A", "Aggressive safe extras: enables optional heavier checks like nikto/testssl."],
        ["-M safe", "Extra modules. Use none, dns, dns-deep, passive, web, http, tls, screenshots, templates, safe, all, full, mission."],
        ["--mission", "Enable passive discovery, DNS deep checks, HTTP detail, TLS, screenshots, and nuclei if installed."],
        ["--scan-preset", "Simple tool behavior: quick, standard, full, web, vuln."],
        ["--raw-dir", "Save raw tool evidence such as headers/subdomains/template output."],
        ["--html", "Save a standalone HTML report."],
        ["--markdown", "Save a Markdown report."],
        ["--diff old.json", "Compare current scan against a previous JSON report."],
        ["-t 180", "Timeout per tool command. Alias for --timeout."],
        ["-o report.json", "Save JSON report. Alias for --json."],
        ["--cmd", "Show exact commands and timings. Alias for --show-commands."],
        ["--explain", "Show this simple switch guide in the report."],
        ["--no-whois", "Skip WHOIS."],
        ["--check-deps", "Show installed/missing dependency status and exit."],
        ["--install-deps", "Install tools best-effort using Linux/macOS package managers plus Go/Python fallbacks."],
        ["--with-optional", "Also install optional web/TLS tools during dependency install."],
        ["--dry-run", "Print install commands without changing the system."],
        ["--ai", "Send scan summary to AI provider from recon_config.json."],
        ["--ai-out", "Save AI answer to a Markdown/text file."],
        ["--ai-prompt", "Print the configured AI system prompt and exit."],
        ["--show-config", "Print loaded AI config without API key and exit."],
        ["--test-ai", "Test AI endpoint/model/API key without running a scan."],
        ["--no-color", "Plain output for logs/CI."],
    ]
    return table(["Switch", "Meaning"], rows, colorize=colorize, max_widths=[18, 88])

def render(report: ReconReport, *, colorize: bool = True, show_commands: bool = False, explain: bool = False) -> str:
    lines = [render_banner(report, colorize=colorize)]
    lines.append(hr("Mission Summary", colorize=colorize))
    lines.append(render_summary(report, colorize=colorize))

    lines.append(hr("Target", colorize=colorize))
    ip_rows = []
    for ip in report.resolved_ips:
        ptr = ", ".join(report.reverse_dns.get(ip, [])) or color("no PTR", C.DIM, colorize)
        ip_rows.append([ip, ptr])
    lines.append(table(["IP", "Reverse DNS"], ip_rows, colorize=colorize, max_widths=[40, 70]))

    lines.append(hr("DNS Intel", colorize=colorize))
    dns_rows = []
    for record in DEFAULT_RECORDS:
        values = report.dns_records.get(record, [])
        if values:
            dns_rows.extend([[record, value] for value in values])
    lines.append(table(["Type", "Value"], dns_rows, colorize=colorize, max_widths=[6, 110]))

    lines.append(hr("Ports & Services", colorize=colorize))
    port_rows = []
    for item in report.nmap_ports:
        severity, state_color = port_severity(item)
        port_rows.append([color(item["port"], C.CYAN, colorize), color(item["state"], state_color, colorize), color(item["service"], C.WHITE, colorize), item["version"], color(severity, state_color, colorize)])
    lines.append(table(["Port", "State", "Service", "Version", "Flag"], port_rows, colorize=colorize, max_widths=[10, 8, 16, 70, 8]))

    lines.append(hr("Executive Brief", colorize=colorize))
    lines.append(render_executive_brief(report, colorize=colorize))

    if report.nmap_ports:
        lines.append(hr("Quick Take", colorize=colorize))
        lines.append(render_findings(report, colorize=colorize))

    lines.append(hr("Suggested Next Checks", colorize=colorize))
    lines.append(render_next_steps(report, colorize=colorize))

    if report.extras:
        lines.append(hr("Extra Tooling", colorize=colorize))
        lines.append(render_extra_tools(report, colorize=colorize))

    if report.artifacts:
        lines.append(hr("Artifacts", colorize=colorize))
        artifact_rows = [[name, path] for name, path in sorted(report.artifacts.items())]
        lines.append(table(["Artifact", "Path"], artifact_rows, colorize=colorize, max_widths=[28, 100]))

    if report.whois_summary:
        lines.append(hr("WHOIS", colorize=colorize))
        lines.extend(f"  {color('◆', C.CYAN, colorize)} {line}" for line in report.whois_summary)

    if explain:
        lines.append(hr("Switch Guide", colorize=colorize))
        lines.append(render_switch_guide(colorize=colorize))

    if show_commands:
        lines.append(hr("Tool Trace", colorize=colorize))
        lines.append(render_commands(report, colorize=colorize))

    if report.notes:
        lines.append(hr("Notes", colorize=colorize))
        lines.extend(f"  {color('!', C.YELLOW, colorize)} {note}" for note in sorted(set(report.notes)))
    return "\n".join(lines)
