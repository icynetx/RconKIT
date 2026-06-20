import concurrent.futures
import socket
import shutil
from pathlib import Path

from .constants import DEFAULT_RECORDS, FAST_PORTS, NMAP_TIMING_ARGS, PROFILE_PORTS, WEB_FALLBACK_PORTS, WEB_PORTS, WEB_SERVICES
from .models import CmdResult, ExtraResult, ReconReport
from .parsers import first_lines, parse_dig_answer, parse_nmap, summarize_host, summarize_nikto, summarize_nslookup, summarize_wafw00f, summarize_whatweb, whois_summary
from .runner import run_cmd, which_tool
from .target import is_ip, target_has_scan_endpoint

def command_record(result: CmdResult) -> dict[str, object]:
    return {
        "command": " ".join(result.command),
        "ok": result.ok,
        "elapsed_seconds": round(result.elapsed, 2),
        "missing": result.missing,
        "stderr": result.stderr,
    }

def add_extra(report: ReconReport, module: str, tool: str, result: CmdResult, summary: list[str]) -> None:
    report.commands.append(command_record(result))
    report.extras.append(ExtraResult(module=module, tool=tool, ok=result.ok, summary=summary, missing=result.missing, elapsed=result.elapsed))
    if result.missing:
        report.notes.append(f"{tool} is not installed; {module} skipped.")

def preset_config(preset: str) -> dict[str, object]:
    presets = {
        "quick": {
            "nmap_timing": "T4", "nmap_retries": 1, "http_rate": 30, "http_retries": 1, "http_timeout": 8,
            "nuclei_rate": 30, "nuclei_c": 15, "nuclei_retries": 1, "nuclei_timeout": 8, "katana_depth": 1, "katana_rate": 20,
        },
        "standard": {
            "nmap_timing": "T3", "nmap_retries": 2, "http_rate": 20, "http_retries": 1, "http_timeout": 12,
            "nuclei_rate": 20, "nuclei_c": 10, "nuclei_retries": 1, "nuclei_timeout": 12, "katana_depth": 1, "katana_rate": 10,
        },
        "full": {
            "nmap_timing": "T3", "nmap_retries": 3, "http_rate": 15, "http_retries": 2, "http_timeout": 20,
            "nuclei_rate": 15, "nuclei_c": 8, "nuclei_retries": 2, "nuclei_timeout": 20, "katana_depth": 2, "katana_rate": 8,
        },
        "web": {
            "nmap_timing": "T3", "nmap_retries": 2, "http_rate": 15, "http_retries": 2, "http_timeout": 15,
            "nuclei_rate": 10, "nuclei_c": 6, "nuclei_retries": 1, "nuclei_timeout": 15, "katana_depth": 2, "katana_rate": 8,
        },
        "vuln": {
            "nmap_timing": "T3", "nmap_retries": 2, "http_rate": 10, "http_retries": 1, "http_timeout": 15,
            "nuclei_rate": 10, "nuclei_c": 6, "nuclei_retries": 1, "nuclei_timeout": 15, "katana_depth": 1, "katana_rate": 8,
        },
    }
    return presets.get(preset, presets["standard"])


def nmap_common_args(default_timing: str, default_retries: int, host_timeout: str, preset: str = "standard") -> list[str]:
    config = preset_config(preset)
    timing = str(config.get("nmap_timing") or default_timing)
    retries = int(config.get("nmap_retries") if config.get("nmap_retries") is not None else default_retries)
    return [f"-{timing}", "--max-retries", str(retries), "--host-timeout", host_timeout]


def httpx_preset_args(preset: str = "standard") -> list[str]:
    config = preset_config(preset)
    args = ["-follow-redirects"]
    args.extend(["-rate-limit", str(config["http_rate"])])
    args.extend(["-retries", str(config["http_retries"])])
    args.extend(["-timeout", str(config["http_timeout"])])
    return args


def curl_preset_args(preset: str = "standard") -> list[str]:
    return []


def katana_preset_args(preset: str = "standard") -> list[str]:
    config = preset_config(preset)
    return ["-depth", str(config["katana_depth"]), "-rate-limit", str(config["katana_rate"])]


def nuclei_preset_args(preset: str = "standard") -> list[str]:
    config = preset_config(preset)
    return [
        "-severity", "info,low,medium,high,critical",
        "-rl", str(config["nuclei_rate"]),
        "-c", str(config["nuclei_c"]),
        "-retries", str(config["nuclei_retries"]),
        "-timeout", str(config["nuclei_timeout"]),
    ]


def python_dns_fallback(target: str, report: ReconReport) -> None:
    try:
        infos = socket.getaddrinfo(target, None, socket.AF_INET, socket.SOCK_STREAM)
        addresses = sorted({item[4][0] for item in infos})
    except socket.gaierror:
        addresses = []
    if addresses and not report.dns_records.get("A"):
        report.dns_records["A"] = addresses
    try:
        infos6 = socket.getaddrinfo(target, None, socket.AF_INET6, socket.SOCK_STREAM)
        addresses6 = sorted({item[4][0] for item in infos6})
    except socket.gaierror:
        addresses6 = []
    if addresses6 and not report.dns_records.get("AAAA"):
        report.dns_records["AAAA"] = addresses6


def scan_dns(target: str, timeout: int, report: ReconReport) -> None:
    if is_ip(target):
        report.notes.append("DNS record scan skipped because target is an IP address.")
        return
    if not which_tool("dig"):
        python_dns_fallback(target, report)
        report.notes.append("dig is not installed; used Python resolver fallback for A/AAAA only.")
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(DEFAULT_RECORDS)) as pool:
        futures = {pool.submit(run_cmd, ["dig", "+short", target, record], timeout): record for record in DEFAULT_RECORDS}
        for future in concurrent.futures.as_completed(futures):
            record = futures[future]
            result = future.result()
            report.commands.append(command_record(result))
            if result.missing:
                python_dns_fallback(target, report)
                report.notes.append("dig is not installed; used Python resolver fallback for A/AAAA only.")
                return
            report.dns_records[record] = parse_dig_answer(result.stdout)

def scan_dns_tools(target: str, timeout: int, report: ReconReport) -> None:
    if is_ip(target):
        return
    dns_timeout = max(5, min(timeout, 12))
    if which_tool("host"):
        host_result = run_cmd(["host", "-a", target], dns_timeout)
        add_extra(report, "DNS Tools", "host", host_result, summarize_host(host_result.stdout))
    else:
        add_extra(report, "DNS Tools", "host", CmdResult(["host"], False, missing=True, stderr="host not found"), [])
    if which_tool("nslookup"):
        ns_result = run_cmd(["nslookup", "-type=any", target], dns_timeout)
        add_extra(report, "DNS Tools", "nslookup", ns_result, summarize_nslookup(ns_result.stdout, ns_result.stderr))
    else:
        add_extra(report, "DNS Tools", "nslookup", CmdResult(["nslookup"], False, missing=True, stderr="nslookup not found"), [])

def scan_nmap(target: str, timeout: int, report: ReconReport, ports: str | None, deep: bool, preset: str = "standard") -> None:
    effective_timeout = max(10, timeout)
    if deep:
        args = ["nmap", "-n", "-oN", "-", "-sV", "-sC", "-Pn"]
        if ports:
            args.extend(["-p", ports])
        else:
            args.extend(["--top-ports", "1000"])
        args.extend([*nmap_common_args("T4", 2, "75s", preset), target])
        result = run_cmd(args, effective_timeout)
        report.commands.append(command_record(result))
        if result.missing:
            report.notes.append("nmap is not installed; port scan skipped.")
            return
        initial_ports = parse_nmap(result.stdout)
        initial_open = [item for item in initial_ports if item["state"] == "open"]
        if initial_open:
            report.nmap_ports = initial_ports
            return
        if result.stderr:
            report.notes.append(f"nmap deep note: {result.stderr[:180]}")
        fallback_ports = ports or FAST_PORTS
        fallback_timeout = max(30, min(effective_timeout, 60))
        fallback_args = ["nmap", "-n", "-oN", "-", "-Pn", *nmap_common_args("T3", 3, f"{fallback_timeout}s", preset), "--open", "-p", fallback_ports, target]
        fallback = run_cmd(fallback_args, effective_timeout)
        report.commands.append(command_record(fallback))
        discovered = parse_nmap(fallback.stdout)
        open_ports = [item["port"].split("/", 1)[0] for item in discovered if item["state"] == "open"]
        if open_ports:
            service_args = ["nmap", "-n", "-oN", "-", "-sV", "--version-light", "-Pn", *nmap_common_args("T3", 2, f"{fallback_timeout}s", preset), "-p", ",".join(open_ports), target]
            service = run_cmd(service_args, effective_timeout)
            report.commands.append(command_record(service))
            report.nmap_ports = parse_nmap(service.stdout) or discovered
            report.notes.append("nmap deep returned no ports; fallback discovery recovered open ports.")
        else:
            report.nmap_ports = initial_ports
            report.notes.append("nmap deep and fallback discovery found no open ports in the selected set.")
        return

    selected_ports = ports or PROFILE_PORTS.get(report.profile, FAST_PORTS)
    effective_timeout = max(10, timeout)
    discovery_timeout = max(10, min(effective_timeout - 5, 30))
    discovery_args = ["nmap", "-n", "-oN", "-", "-Pn", *nmap_common_args("T4", 1, f"{discovery_timeout}s", preset), "--open", "-p", selected_ports, target]
    discovery = run_cmd(discovery_args, effective_timeout)
    report.commands.append(command_record(discovery))
    if discovery.missing:
        report.notes.append("nmap is not installed; port scan skipped.")
        return

    open_ports = [item["port"].split("/", 1)[0] for item in parse_nmap(discovery.stdout) if item["state"] == "open"]
    if not open_ports and not ports and report.profile == "fast":
        fallback_timeout = max(15, min(effective_timeout - 5, 45))
        fallback_args = ["nmap", "-n", "-oN", "-", "-Pn", *nmap_common_args("T3", 3, f"{fallback_timeout}s", preset), "--open", "-p", WEB_FALLBACK_PORTS, target]
        fallback = run_cmd(fallback_args, effective_timeout)
        report.commands.append(command_record(fallback))
        fallback_ports = [item["port"].split("/", 1)[0] for item in parse_nmap(fallback.stdout) if item["state"] == "open"]
        if fallback_ports:
            open_ports = fallback_ports
            report.notes.append("nmap fallback recovered open web ports after the broad fast pass returned none.")

    if not open_ports:
        if discovery.stderr:
            report.notes.append(f"nmap discovery note: {discovery.stderr[:180]}")
        report.notes.append("nmap discovery found no open ports in the selected port set. Try --mode balanced or -p 80,443,8080,8443.")
        return

    service_args = ["nmap", "-n", "-oN", "-", "-sV", "--version-light", "-Pn", *nmap_common_args("T4", 1, f"{discovery_timeout}s", preset), "-p", ",".join(open_ports), target]
    service = run_cmd(service_args, effective_timeout)
    report.commands.append(command_record(service))
    report.nmap_ports = parse_nmap(service.stdout) or parse_nmap(discovery.stdout)
    if service.stderr:
        report.notes.append(f"nmap service note: {service.stderr[:180]}")

def scan_whois(target: str, timeout: int, report: ReconReport) -> None:
    result = run_cmd(["whois", target], timeout)
    report.commands.append(command_record(result))
    if result.missing:
        report.notes.append("whois is not installed; WHOIS summary skipped.")
        return
    report.whois_summary = whois_summary(result.stdout)

def web_urls(report: ReconReport) -> list[str]:
    if not target_has_scan_endpoint(report):
        return []
    urls: list[str] = []
    for item in report.nmap_ports:
        port = item["port"].split("/", 1)[0]
        service = item["service"].lower()
        if port not in WEB_PORTS and service not in WEB_SERVICES:
            continue
        scheme = "https" if port in {"443", "8443", "2083", "2087", "2096"} or "ssl" in service or service == "https" else "http"
        default = (scheme == "http" and port == "80") or (scheme == "https" and port == "443")
        suffix = "" if default else f":{port}"
        urls.append(f"{scheme}://{report.normalized_target}{suffix}")
    if not urls and not is_ip(report.normalized_target):
        urls = [f"http://{report.normalized_target}", f"https://{report.normalized_target}"]
    return list(dict.fromkeys(urls))

def scan_web_stack(report: ReconReport, timeout: int, aggressive: bool, preset: str = "standard") -> None:
    urls = web_urls(report)
    if not urls:
        report.notes.append("No web-looking ports found; web tooling skipped.")
        return

    if which_tool("whatweb"):
        result = run_cmd(["whatweb", "--color=never", "--no-errors", "--log-brief=-", *urls[:6]], timeout)
        add_extra(report, "Web Fingerprint", "whatweb", result, summarize_whatweb(result.stdout))
    else:
        add_extra(report, "Web Fingerprint", "whatweb", CmdResult(["whatweb"], False, missing=True, stderr="whatweb not found"), [])

    httpx_bin = which_tool("httpx") or which_tool("httpx-toolkit")
    if httpx_bin:
        result = run_cmd([httpx_bin, "-silent", "-title", "-tech-detect", "-status-code", *httpx_preset_args(preset), "-u", urls[0]], timeout)
        add_extra(report, "HTTP Probe", Path(httpx_bin).name, result, first_lines(result.stdout, 8))
    else:
        add_extra(report, "HTTP Probe", "httpx", CmdResult(["httpx"], False, missing=True, stderr="httpx not found"), [])

    if which_tool("wafw00f"):
        result = run_cmd(["wafw00f", "-a", urls[0]], timeout)
        add_extra(report, "WAF Check", "wafw00f", result, summarize_wafw00f(result.stdout))
    else:
        add_extra(report, "WAF Check", "wafw00f", CmdResult(["wafw00f"], False, missing=True, stderr="wafw00f not found"), [])

    if aggressive and which_tool("nikto"):
        result = run_cmd(["nikto", "-nointeractive", "-Tuning", "x", "-host", urls[0]], timeout)
        add_extra(report, "Web Baseline", "nikto", result, summarize_nikto(result.stdout))
    elif aggressive:
        add_extra(report, "Web Baseline", "nikto", CmdResult(["nikto"], False, missing=True, stderr="nikto not found"), [])

def scan_tls(report: ReconReport, timeout: int, aggressive: bool) -> None:
    tls_targets = []
    for item in report.nmap_ports:
        port = item["port"].split("/", 1)[0]
        service = item["service"].lower()
        if port in {"443", "8443", "2083", "2087", "2096", "465", "993", "995"} or "ssl" in service or service == "https":
            tls_targets.append(f"{report.normalized_target}:{port}")
    tls_targets = list(dict.fromkeys(tls_targets))[:4]
    if not tls_targets:
        return

    if which_tool("sslscan"):
        result = run_cmd(["sslscan", "--no-colour", tls_targets[0]], timeout)
        interesting = [line.strip() for line in result.stdout.splitlines() if any(token in line for token in ("SSLv", "TLSv", "Subject:", "Issuer:", "Signature Algorithm", "not vulnerable"))]
        add_extra(report, "TLS Check", "sslscan", result, list(dict.fromkeys(interesting))[:8])
    elif which_tool("testssl.sh") and aggressive:
        result = run_cmd(["testssl.sh", "--fast", "--warnings", "batch", tls_targets[0]], timeout)
        add_extra(report, "TLS Check", "testssl.sh", result, first_lines(result.stdout, 12))
    else:
        report.notes.append("sslscan not installed; TLS detail skipped.")

def scan_extra_modules(report: ReconReport, timeout: int, modules: set[str], aggressive: bool, raw_dir: Path | None = None, preset: str = "standard") -> None:
    if "passive" in modules:
        scan_passive(report, timeout, raw_dir)
    if "dns-tools" in modules:
        scan_dns_tools(report.normalized_target, timeout, report)
    if "dns-deep" in modules:
        scan_dns_deep(report, timeout, raw_dir)
    if not target_has_scan_endpoint(report):
        skipped = sorted(modules & {"web", "tls", "http-detail", "screenshots", "templates"})
        if skipped:
            report.notes.append(f"No resolved IPs for target; skipped endpoint modules: {', '.join(skipped)}.")
        return
    if "web" in modules:
        scan_web_stack(report, timeout, aggressive, preset)
    if "http-detail" in modules:
        scan_http_detail(report, timeout, raw_dir, preset)
    if "tls" in modules:
        scan_tls(report, timeout, aggressive)
    if "screenshots" in modules:
        scan_screenshots(report, timeout, raw_dir, preset)
    if "templates" in modules:
        scan_templates(report, timeout, raw_dir, preset)

def parse_modules(raw: str) -> set[str]:
    aliases = {
        "safe": {"dns-tools", "web", "tls"},
        "all": {"dns-tools", "dns-deep", "web", "http-detail", "tls", "passive"},
        "full": {"dns-tools", "dns-deep", "web", "http-detail", "tls", "passive", "screenshots", "templates"},
        "mission": {"dns-tools", "dns-deep", "web", "http-detail", "tls", "passive", "screenshots", "templates"},
        "none": set(),
        "dns": {"dns-tools"},
        "dns-tools": {"dns-tools"},
        "dns-deep": {"dns-deep"},
        "passive": {"passive"},
        "subdomains": {"passive"},
        "web": {"web"},
        "http": {"web", "http-detail"},
        "http-detail": {"http-detail"},
        "tls": {"tls"},
        "ssl": {"tls"},
        "screenshots": {"screenshots"},
        "shots": {"screenshots"},
        "templates": {"templates"},
        "nuclei": {"templates"},
    }
    modules: set[str] = set()
    for item in [part.strip().lower() for part in raw.split(",") if part.strip()]:
        if item not in aliases:
            raise ValueError(f"unknown module '{item}'")
        modules |= aliases[item]
    return modules


def save_artifact(report: ReconReport, raw_dir: Path | None, name: str, content: str) -> None:
    if not raw_dir or not content:
        return
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("/", "_").replace(" ", "_")
    path = raw_dir / safe_name
    path.write_text(content.strip() + "\n", encoding="utf-8")
    report.artifacts[safe_name] = str(path)


def scan_passive(report: ReconReport, timeout: int, raw_dir: Path | None = None) -> None:
    if is_ip(report.normalized_target):
        report.notes.append("Passive subdomain discovery skipped because target is an IP address.")
        return
    if which_tool("subfinder"):
        result = run_cmd(["subfinder", "-silent", "-d", report.normalized_target], timeout)
        save_artifact(report, raw_dir, "subfinder.txt", result.stdout)
        add_extra(report, "Passive Discovery", "subfinder", result, first_lines(result.stdout, 12))
    else:
        add_extra(report, "Passive Discovery", "subfinder", CmdResult(["subfinder"], False, missing=True, stderr="subfinder not found"), [])

    if which_tool("amass"):
        result = run_cmd(["amass", "enum", "-passive", "-norecursive", "-d", report.normalized_target], timeout)
        save_artifact(report, raw_dir, "amass-passive.txt", result.stdout)
        add_extra(report, "Passive Discovery", "amass", result, first_lines(result.stdout, 12))
    else:
        add_extra(report, "Passive Discovery", "amass", CmdResult(["amass"], False, missing=True, stderr="amass not found"), [])


def scan_dns_deep(report: ReconReport, timeout: int, raw_dir: Path | None = None) -> None:
    if is_ip(report.normalized_target):
        return
    resolver = report.resolved_ips[0] if report.resolved_ips else report.normalized_target
    axfr = run_cmd(["dig", "axfr", f"@{resolver}", report.normalized_target], min(timeout, 20))
    save_artifact(report, raw_dir, "dig-axfr.txt", axfr.stdout or axfr.stderr)
    summary = first_lines(axfr.stdout or axfr.stderr, 8)
    if axfr.ok and "Transfer failed" not in axfr.stdout and "failed" not in axfr.stdout.lower() and len(axfr.stdout.splitlines()) > 3:
        report.notes.append("DNS AXFR returned data; verify zone-transfer restrictions immediately.")
    add_extra(report, "DNS Deep", "dig-axfr", axfr, summary)


def scan_http_detail(report: ReconReport, timeout: int, raw_dir: Path | None = None, preset: str = "standard") -> None:
    urls = web_urls(report)
    if not urls:
        report.notes.append("HTTP detail skipped because no web URL was identified.")
        return
    for index, url in enumerate(urls[:4], 1):
        if which_tool("curl"):
            curl_timeout = min(timeout, int(preset_config(preset).get("http_timeout", 20)))
            result = run_cmd(["curl", "-k", "-L", "-I", "--max-time", str(curl_timeout), *curl_preset_args(preset), url], min(timeout, 25))
            save_artifact(report, raw_dir, f"curl-headers-{index}.txt", result.stdout or result.stderr)
            headers = [line.strip() for line in result.stdout.splitlines() if ":" in line][:10]
            add_extra(report, "HTTP Headers", "curl", result, headers or first_lines(result.stdout or result.stderr, 8))
        else:
            add_extra(report, "HTTP Headers", "curl", CmdResult(["curl"], False, missing=True, stderr="curl not found"), [])
            break
    if which_tool("katana"):
        result = run_cmd(["katana", "-silent", "-no-color", *katana_preset_args(preset), "-u", urls[0]], min(timeout, 45))
        save_artifact(report, raw_dir, "katana-depth1.txt", result.stdout)
        add_extra(report, "HTTP Crawl", "katana", result, first_lines(result.stdout, 12))
    else:
        report.notes.append("katana not installed; safe crawl skipped.")


def scan_screenshots(report: ReconReport, timeout: int, raw_dir: Path | None = None, preset: str = "standard") -> None:
    urls = web_urls(report)
    if not urls:
        return
    if not which_tool("gowitness"):
        add_extra(report, "Screenshots", "gowitness", CmdResult(["gowitness"], False, missing=True, stderr="gowitness not found"), [])
        return
    out_dir = (raw_dir or Path("recon-artifacts")) / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_cmd(["gowitness", "scan", "single", "--url", urls[0], "--screenshot-path", str(out_dir)], min(timeout, 60))
    save_artifact(report, raw_dir, "gowitness.txt", result.stdout or result.stderr)
    add_extra(report, "Screenshots", "gowitness", result, first_lines(result.stdout or result.stderr, 8))


def scan_templates(report: ReconReport, timeout: int, raw_dir: Path | None = None, preset: str = "standard") -> None:
    urls = web_urls(report)
    if not urls:
        return
    if not which_tool("nuclei"):
        add_extra(report, "Template Checks", "nuclei", CmdResult(["nuclei"], False, missing=True, stderr="nuclei not found"), [])
        return
    result = run_cmd(["nuclei", "-silent", "-no-color", *nuclei_preset_args(preset), "-u", urls[0]], min(timeout, 90))
    save_artifact(report, raw_dir, "nuclei.txt", result.stdout or result.stderr)
    add_extra(report, "Template Checks", "nuclei", result, first_lines(result.stdout or result.stderr, 12))
