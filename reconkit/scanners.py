import concurrent.futures
import socket
import shutil
from pathlib import Path

from .constants import DEFAULT_RECORDS, FAST_PORTS, NMAP_TIMING_ARGS, PROFILE_PORTS, WEB_FALLBACK_PORTS, WEB_PORTS, WEB_SERVICES
from .models import CmdResult, ExtraResult, ReconReport
from .parsers import first_lines, parse_dig_answer, parse_nmap, summarize_host, summarize_nikto, summarize_nslookup, summarize_wafw00f, summarize_whatweb, whois_summary
from .presets import preset_base, preset_strategy, preset_tool_args
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
    return presets.get(preset_base(preset), presets["standard"])


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


def custom_args(preset: str, tool: str) -> list[str]:
    return preset_tool_args(preset, tool)


def preset_only(preset: str) -> bool:
    return preset_strategy(preset) == "only"


def replace_args(preset: str, tool: str) -> list[str]:
    args = custom_args(preset, tool)
    return args if preset_strategy(preset) in {"replace", "only"} and args else []


def with_placeholders(args: list[str], *, target: str | None = None, url: str | None = None, domain: str | None = None, out_dir: str | None = None) -> list[str]:
    replacements = {
        "{target}": target or "",
        "{url}": url or "",
        "{domain}": domain or target or "",
        "{out_dir}": out_dir or "",
    }
    rendered = []
    for arg in args:
        value = arg
        for key, replacement in replacements.items():
            value = value.replace(key, replacement)
        rendered.append(value)
    return rendered


def command_from_preset(binary: str, args: list[str], fallback_target: str, placeholder: str = "{target}") -> list[str]:
    rendered = with_placeholders(args, target=fallback_target, url=fallback_target, domain=fallback_target)
    placeholders = ("{target}", "{url}", "{domain}", "{out_dir}", placeholder)
    if not any(any(token in arg for token in placeholders) for arg in args):
        rendered.append(fallback_target)
    return [binary, *rendered]


def has_flag(args: list[str], *flags: str) -> bool:
    return any(arg in flags or any(arg.startswith(flag + "=") for flag in flags if flag.startswith("--")) for arg in args)


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

def scan_dns_tools(target: str, timeout: int, report: ReconReport, preset: str = "standard") -> None:
    if is_ip(target):
        return
    dns_timeout = max(5, min(timeout, 12))
    if preset_only(preset) and not custom_args(preset, "host"):
        pass
    elif which_tool("host"):
        host_replace = replace_args(preset, "host")
        host_cmd = command_from_preset("host", host_replace, target) if host_replace else ["host", "-a", target, *custom_args(preset, "host")]
        host_result = run_cmd(host_cmd, dns_timeout)
        add_extra(report, "DNS Tools", "host", host_result, summarize_host(host_result.stdout))
    else:
        add_extra(report, "DNS Tools", "host", CmdResult(["host"], False, missing=True, stderr="host not found"), [])
    if preset_only(preset) and not custom_args(preset, "nslookup"):
        pass
    elif which_tool("nslookup"):
        ns_replace = replace_args(preset, "nslookup")
        ns_cmd = command_from_preset("nslookup", ns_replace, target) if ns_replace else ["nslookup", "-type=any", target, *custom_args(preset, "nslookup")]
        ns_result = run_cmd(ns_cmd, dns_timeout)
        add_extra(report, "DNS Tools", "nslookup", ns_result, summarize_nslookup(ns_result.stdout, ns_result.stderr))
    else:
        add_extra(report, "DNS Tools", "nslookup", CmdResult(["nslookup"], False, missing=True, stderr="nslookup not found"), [])

def scan_nmap(target: str, timeout: int, report: ReconReport, ports: str | None, deep: bool, preset: str = "standard") -> None:
    effective_timeout = max(10, timeout)
    nmap_replace = replace_args(preset, "nmap")
    if preset_only(preset) and not nmap_replace:
        report.notes.append("nmap skipped because scan preset mode is only and nmap has no preset args.")
        return
    if nmap_replace:
        result = run_cmd(command_from_preset("nmap", nmap_replace, target), effective_timeout)
        report.commands.append(command_record(result))
        if result.missing:
            report.notes.append("nmap is not installed; port scan skipped.")
            return
        report.nmap_ports = parse_nmap(result.stdout)
        if not report.nmap_ports and result.stderr:
            report.notes.append(f"custom nmap preset note: {result.stderr[:180]}")
        return
    if deep:
        args = ["nmap", "-n", "-oN", "-", "-sV", "-sC", "-Pn"]
        if ports:
            args.extend(["-p", ports])
        else:
            args.extend(["--top-ports", "1000"])
        args.extend([*nmap_common_args("T4", 2, "75s", preset), *custom_args(preset, "nmap"), target])
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
        fallback_args = ["nmap", "-n", "-oN", "-", "-Pn", *nmap_common_args("T3", 3, f"{fallback_timeout}s", preset), "--open", "-p", fallback_ports, *custom_args(preset, "nmap"), target]
        fallback = run_cmd(fallback_args, effective_timeout)
        report.commands.append(command_record(fallback))
        discovered = parse_nmap(fallback.stdout)
        open_ports = [item["port"].split("/", 1)[0] for item in discovered if item["state"] == "open"]
        if open_ports:
            service_args = ["nmap", "-n", "-oN", "-", "-sV", "--version-light", "-Pn", *nmap_common_args("T3", 2, f"{fallback_timeout}s", preset), "-p", ",".join(open_ports), *custom_args(preset, "nmap"), target]
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
    discovery_args = ["nmap", "-n", "-oN", "-", "-Pn", *nmap_common_args("T4", 1, f"{discovery_timeout}s", preset), "--open", "-p", selected_ports, *custom_args(preset, "nmap"), target]
    discovery = run_cmd(discovery_args, effective_timeout)
    report.commands.append(command_record(discovery))
    if discovery.missing:
        report.notes.append("nmap is not installed; port scan skipped.")
        return

    open_ports = [item["port"].split("/", 1)[0] for item in parse_nmap(discovery.stdout) if item["state"] == "open"]
    if not open_ports and not ports and report.profile == "fast":
        fallback_timeout = max(15, min(effective_timeout - 5, 45))
        fallback_args = ["nmap", "-n", "-oN", "-", "-Pn", *nmap_common_args("T3", 3, f"{fallback_timeout}s", preset), "--open", "-p", WEB_FALLBACK_PORTS, *custom_args(preset, "nmap"), target]
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

    service_args = ["nmap", "-n", "-oN", "-", "-sV", "--version-light", "-Pn", *nmap_common_args("T4", 1, f"{discovery_timeout}s", preset), "-p", ",".join(open_ports), *custom_args(preset, "nmap"), target]
    service = run_cmd(service_args, effective_timeout)
    report.commands.append(command_record(service))
    report.nmap_ports = parse_nmap(service.stdout) or parse_nmap(discovery.stdout)
    if service.stderr:
        report.notes.append(f"nmap service note: {service.stderr[:180]}")

def scan_whois(target: str, timeout: int, report: ReconReport, preset: str = "standard") -> None:
    if preset_only(preset) and not custom_args(preset, "whois"):
        report.notes.append("WHOIS skipped because scan preset mode is only and whois has no preset args.")
        return
    whois_replace = replace_args(preset, "whois")
    result = run_cmd(command_from_preset("whois", whois_replace, target) if whois_replace else ["whois", target, *custom_args(preset, "whois")], timeout)
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

    if preset_only(preset) and not custom_args(preset, "whatweb"):
        pass
    elif which_tool("whatweb"):
        whatweb_replace = replace_args(preset, "whatweb")
        whatweb_cmd = ["whatweb", *with_placeholders(whatweb_replace, url=urls[0], target=report.normalized_target, domain=report.normalized_target)]
        if whatweb_replace and not any("{url}" in arg or "{target}" in arg or "{domain}" in arg for arg in whatweb_replace):
            whatweb_cmd.extend(urls[:6])
        if not whatweb_replace:
            whatweb_cmd = ["whatweb", "--color=never", "--no-errors", "--log-brief=-", *custom_args(preset, "whatweb"), *urls[:6]]
        result = run_cmd(whatweb_cmd, timeout)
        add_extra(report, "Web Fingerprint", "whatweb", result, summarize_whatweb(result.stdout))
    else:
        add_extra(report, "Web Fingerprint", "whatweb", CmdResult(["whatweb"], False, missing=True, stderr="whatweb not found"), [])

    httpx_bin = which_tool("httpx") or which_tool("httpx-toolkit")
    if preset_only(preset) and not custom_args(preset, "httpx"):
        pass
    elif httpx_bin:
        httpx_replace = replace_args(preset, "httpx")
        if httpx_replace:
            rendered = with_placeholders(httpx_replace, url=urls[0], target=report.normalized_target, domain=report.normalized_target)
            if not any("{url}" in arg or "{target}" in arg or "{domain}" in arg for arg in httpx_replace) and not has_flag(rendered, "-u", "-l"):
                rendered.extend(["-u", urls[0]])
            result = run_cmd([httpx_bin, *rendered], timeout)
        else:
            result = run_cmd([httpx_bin, "-silent", "-title", "-tech-detect", "-status-code", *httpx_preset_args(preset), *custom_args(preset, "httpx"), "-u", urls[0]], timeout)
        add_extra(report, "HTTP Probe", Path(httpx_bin).name, result, first_lines(result.stdout, 8))
    else:
        add_extra(report, "HTTP Probe", "httpx", CmdResult(["httpx"], False, missing=True, stderr="httpx not found"), [])

    if preset_only(preset) and not custom_args(preset, "wafw00f"):
        pass
    elif which_tool("wafw00f"):
        wafw00f_replace = replace_args(preset, "wafw00f")
        result = run_cmd(command_from_preset("wafw00f", wafw00f_replace, urls[0], "{url}") if wafw00f_replace else ["wafw00f", "-a", urls[0], *custom_args(preset, "wafw00f")], timeout)
        add_extra(report, "WAF Check", "wafw00f", result, summarize_wafw00f(result.stdout))
    else:
        add_extra(report, "WAF Check", "wafw00f", CmdResult(["wafw00f"], False, missing=True, stderr="wafw00f not found"), [])

    if preset_only(preset) and not custom_args(preset, "nikto"):
        pass
    elif aggressive and which_tool("nikto"):
        nikto_replace = replace_args(preset, "nikto")
        if nikto_replace:
            rendered = with_placeholders(nikto_replace, url=urls[0], target=report.normalized_target, domain=report.normalized_target)
            if not any("{url}" in arg or "{target}" in arg or "{domain}" in arg for arg in nikto_replace) and not has_flag(rendered, "-host", "-h"):
                rendered.extend(["-host", urls[0]])
            result = run_cmd(["nikto", *rendered], timeout)
        else:
            result = run_cmd(["nikto", "-nointeractive", "-Tuning", "x", "-host", urls[0], *custom_args(preset, "nikto")], timeout)
        add_extra(report, "Web Baseline", "nikto", result, summarize_nikto(result.stdout))
    elif aggressive:
        add_extra(report, "Web Baseline", "nikto", CmdResult(["nikto"], False, missing=True, stderr="nikto not found"), [])

def scan_tls(report: ReconReport, timeout: int, aggressive: bool, preset: str = "standard") -> None:
    tls_targets = []
    for item in report.nmap_ports:
        port = item["port"].split("/", 1)[0]
        service = item["service"].lower()
        if port in {"443", "8443", "2083", "2087", "2096", "465", "993", "995"} or "ssl" in service or service == "https":
            tls_targets.append(f"{report.normalized_target}:{port}")
    tls_targets = list(dict.fromkeys(tls_targets))[:4]
    if not tls_targets:
        return

    if preset_only(preset) and not custom_args(preset, "sslscan"):
        pass
    elif which_tool("sslscan"):
        sslscan_replace = replace_args(preset, "sslscan")
        result = run_cmd(command_from_preset("sslscan", sslscan_replace, tls_targets[0]) if sslscan_replace else ["sslscan", "--no-colour", *custom_args(preset, "sslscan"), tls_targets[0]], timeout)
        interesting = [line.strip() for line in result.stdout.splitlines() if any(token in line for token in ("SSLv", "TLSv", "Subject:", "Issuer:", "Signature Algorithm", "not vulnerable"))]
        add_extra(report, "TLS Check", "sslscan", result, list(dict.fromkeys(interesting))[:8])
    elif preset_only(preset) and not custom_args(preset, "testssl.sh"):
        pass
    elif which_tool("testssl.sh") and aggressive:
        testssl_replace = replace_args(preset, "testssl.sh")
        result = run_cmd(command_from_preset("testssl.sh", testssl_replace, tls_targets[0]) if testssl_replace else ["testssl.sh", "--fast", "--warnings", "batch", *custom_args(preset, "testssl.sh"), tls_targets[0]], timeout)
        add_extra(report, "TLS Check", "testssl.sh", result, first_lines(result.stdout, 12))
    else:
        report.notes.append("sslscan not installed; TLS detail skipped.")

def scan_extra_modules(report: ReconReport, timeout: int, modules: set[str], aggressive: bool, raw_dir: Path | None = None, preset: str = "standard") -> None:
    if "passive" in modules:
        scan_passive(report, timeout, raw_dir, preset)
    if "dns-tools" in modules:
        scan_dns_tools(report.normalized_target, timeout, report, preset)
    if "dns-deep" in modules:
        scan_dns_deep(report, timeout, raw_dir, preset)
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
        scan_tls(report, timeout, aggressive, preset)
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


def scan_passive(report: ReconReport, timeout: int, raw_dir: Path | None = None, preset: str = "standard") -> None:
    if is_ip(report.normalized_target):
        report.notes.append("Passive subdomain discovery skipped because target is an IP address.")
        return
    if preset_only(preset) and not custom_args(preset, "subfinder"):
        pass
    elif which_tool("subfinder"):
        subfinder_replace = replace_args(preset, "subfinder")
        if subfinder_replace:
            rendered = with_placeholders(subfinder_replace, target=report.normalized_target, domain=report.normalized_target)
            if not any("{target}" in arg or "{domain}" in arg for arg in subfinder_replace) and not has_flag(rendered, "-d"):
                rendered.extend(["-d", report.normalized_target])
            result = run_cmd(["subfinder", *rendered], timeout)
        else:
            result = run_cmd(["subfinder", "-silent", "-d", report.normalized_target, *custom_args(preset, "subfinder")], timeout)
        save_artifact(report, raw_dir, "subfinder.txt", result.stdout)
        add_extra(report, "Passive Discovery", "subfinder", result, first_lines(result.stdout, 12))
    else:
        add_extra(report, "Passive Discovery", "subfinder", CmdResult(["subfinder"], False, missing=True, stderr="subfinder not found"), [])

    if preset_only(preset) and not custom_args(preset, "amass"):
        pass
    elif which_tool("amass"):
        amass_replace = replace_args(preset, "amass")
        if amass_replace:
            rendered = with_placeholders(amass_replace, target=report.normalized_target, domain=report.normalized_target)
            if not any("{target}" in arg or "{domain}" in arg for arg in amass_replace) and not has_flag(rendered, "-d"):
                rendered.extend(["-d", report.normalized_target])
            result = run_cmd(["amass", *rendered], timeout)
        else:
            result = run_cmd(["amass", "enum", "-passive", "-norecursive", "-d", report.normalized_target, *custom_args(preset, "amass")], timeout)
        save_artifact(report, raw_dir, "amass-passive.txt", result.stdout)
        add_extra(report, "Passive Discovery", "amass", result, first_lines(result.stdout, 12))
    else:
        add_extra(report, "Passive Discovery", "amass", CmdResult(["amass"], False, missing=True, stderr="amass not found"), [])


def scan_dns_deep(report: ReconReport, timeout: int, raw_dir: Path | None = None, preset: str = "standard") -> None:
    if is_ip(report.normalized_target):
        return
    if preset_only(preset) and not custom_args(preset, "dig"):
        report.notes.append("DNS deep skipped because scan preset mode is only and dig has no preset args.")
        return
    resolver = report.resolved_ips[0] if report.resolved_ips else report.normalized_target
    dig_replace = replace_args(preset, "dig")
    axfr = run_cmd(command_from_preset("dig", dig_replace, report.normalized_target) if dig_replace else ["dig", "axfr", f"@{resolver}", report.normalized_target, *custom_args(preset, "dig")], min(timeout, 20))
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
        if preset_only(preset) and not custom_args(preset, "curl"):
            continue
        if which_tool("curl"):
            curl_timeout = min(timeout, int(preset_config(preset).get("http_timeout", 20)))
            curl_replace = replace_args(preset, "curl")
            result = run_cmd(command_from_preset("curl", curl_replace, url, "{url}") if curl_replace else ["curl", "-k", "-L", "-I", "--max-time", str(curl_timeout), *curl_preset_args(preset), *custom_args(preset, "curl"), url], min(timeout, 25))
            save_artifact(report, raw_dir, f"curl-headers-{index}.txt", result.stdout or result.stderr)
            headers = [line.strip() for line in result.stdout.splitlines() if ":" in line][:10]
            add_extra(report, "HTTP Headers", "curl", result, headers or first_lines(result.stdout or result.stderr, 8))
        else:
            add_extra(report, "HTTP Headers", "curl", CmdResult(["curl"], False, missing=True, stderr="curl not found"), [])
            break
    if preset_only(preset) and not custom_args(preset, "katana"):
        pass
    elif which_tool("katana"):
        katana_replace = replace_args(preset, "katana")
        if katana_replace:
            rendered = with_placeholders(katana_replace, url=urls[0], target=report.normalized_target, domain=report.normalized_target)
            if not any("{url}" in arg or "{target}" in arg or "{domain}" in arg for arg in katana_replace) and not has_flag(rendered, "-u", "-list"):
                rendered.extend(["-u", urls[0]])
            result = run_cmd(["katana", *rendered], min(timeout, 45))
        else:
            result = run_cmd(["katana", "-silent", "-no-color", *katana_preset_args(preset), *custom_args(preset, "katana"), "-u", urls[0]], min(timeout, 45))
        save_artifact(report, raw_dir, "katana-depth1.txt", result.stdout)
        add_extra(report, "HTTP Crawl", "katana", result, first_lines(result.stdout, 12))
    else:
        report.notes.append("katana not installed; safe crawl skipped.")


def scan_screenshots(report: ReconReport, timeout: int, raw_dir: Path | None = None, preset: str = "standard") -> None:
    urls = web_urls(report)
    if not urls:
        return
    if preset_only(preset) and not custom_args(preset, "gowitness"):
        return
    if not which_tool("gowitness"):
        add_extra(report, "Screenshots", "gowitness", CmdResult(["gowitness"], False, missing=True, stderr="gowitness not found"), [])
        return
    out_dir = (raw_dir or Path("recon-artifacts")) / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    gowitness_replace = replace_args(preset, "gowitness")
    if gowitness_replace:
        rendered = with_placeholders(gowitness_replace, url=urls[0], target=report.normalized_target, domain=report.normalized_target, out_dir=str(out_dir))
        if not any("{url}" in arg or "{target}" in arg or "{domain}" in arg for arg in gowitness_replace) and not has_flag(rendered, "--url"):
            rendered.extend(["--url", urls[0]])
        if not any("{out_dir}" in arg for arg in gowitness_replace) and not has_flag(rendered, "--screenshot-path"):
            rendered.extend(["--screenshot-path", str(out_dir)])
        result = run_cmd(["gowitness", *rendered], min(timeout, 60))
    else:
        result = run_cmd(["gowitness", "scan", "single", "--url", urls[0], "--screenshot-path", str(out_dir), *custom_args(preset, "gowitness")], min(timeout, 60))
    save_artifact(report, raw_dir, "gowitness.txt", result.stdout or result.stderr)
    add_extra(report, "Screenshots", "gowitness", result, first_lines(result.stdout or result.stderr, 8))


def scan_templates(report: ReconReport, timeout: int, raw_dir: Path | None = None, preset: str = "standard") -> None:
    urls = web_urls(report)
    if not urls:
        return
    if preset_only(preset) and not custom_args(preset, "nuclei"):
        return
    if not which_tool("nuclei"):
        add_extra(report, "Template Checks", "nuclei", CmdResult(["nuclei"], False, missing=True, stderr="nuclei not found"), [])
        return
    nuclei_replace = replace_args(preset, "nuclei")
    if nuclei_replace:
        rendered = with_placeholders(nuclei_replace, url=urls[0], target=report.normalized_target, domain=report.normalized_target)
        if not any("{url}" in arg or "{target}" in arg or "{domain}" in arg for arg in nuclei_replace) and not has_flag(rendered, "-u", "-l"):
            rendered.extend(["-u", urls[0]])
        result = run_cmd(["nuclei", *rendered], min(timeout, 90))
    else:
        result = run_cmd(["nuclei", "-silent", "-no-color", *nuclei_preset_args(preset), *custom_args(preset, "nuclei"), "-u", urls[0]], min(timeout, 90))
    save_artifact(report, raw_dir, "nuclei.txt", result.stdout or result.stderr)
    add_extra(report, "Template Checks", "nuclei", result, first_lines(result.stdout or result.stderr, 12))
