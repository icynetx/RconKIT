import argparse
import json
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

from .ai import ai_api_key, ai_key_hint, call_openrouter, load_config, render_ai_analysis, safe_config_for_display, test_ai_connection, validate_ai_config
from .constants import APP, AUTHOR, COPYRIGHT, TAGLINE, TELEGRAM, VERSION, WEBSITE
from .console import run_console
from .deps import install_deps, print_dependencies
from .models import ReconReport
from .render import render
from .reports import diff_reports, save_html, save_json, save_markdown
from .scanners import parse_modules, scan_dns, scan_extra_modules, scan_nmap, scan_whois
from .self_install import install_command_entry
from .target import normalize_target, resolve_target, reverse_lookup, target_has_scan_endpoint
from .ui import C, box, color, hr, pill, table

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="recon.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=color(f"{APP} v{VERSION} by {AUTHOR} - {TAGLINE}", C.BOLD + C.CYAN, sys.stdout.isatty()),
        epilog=textwrap.dedent(
            """
            Simple examples:
              python3 recon.py example.com
              python3 recon.py example.com -m balanced --cmd
              python3 recon.py example.com -p 80,443,8080 -M web,tls
              python3 recon.py example.com --mission --raw-dir artifacts -o scan.json --html report.html
              python3 recon.py example.com -m deep -t 180 -A --explain
              python3 recon.py 1.1.1.1 --no-whois -o report.json
              python3 recon.py --self-install --user        # install reconkit command only
              python3 recon.py --self-install --install-deps --with-optional
              reconkit --install-deps --with-optional
              OPENROUTER_API_KEY=sk-or-... python3 recon.py example.com --ai
              nano recon_config.json   # edit AI endpoint/model/system_prompt
              python3 recon.py --test-ai
              reconkit                                # opens interactive console
              reconkit example.com                    # direct one-shot scan

            Console commands after running reconkit:
              help, show options, set target example.com, set mode deep, run, mission example.com, install, test ai, exit

            Modes:
              fast      Default. Quick and good-looking output.
              balanced  More ports, still safe.
              deep      Slower nmap scripts/service detection on top 1000.

            Modules (-M): none, dns, dns-deep, passive, web, http, tls, screenshots, templates, safe, all, full, mission
              safe      DNS tools + web fingerprint + TLS checks.
              all       Adds passive discovery, DNS AXFR validation, and HTTP detail.
              mission   Adds screenshots and nuclei template checks when installed.
              -A        Adds heavier optional checks such as nikto/testssl when available.

            Only scan systems you own or have explicit permission to test.

            Team CynetX: https://cynetx.ir  |  Telegram: https://t.me/cynetx
            """
        ),
    )
    parser.add_argument("target", nargs="?", help="domain, IP, or URL")
    parser.add_argument("-m", "--mode", "--profile", choices=("fast", "balanced", "deep"), default="fast", help="scan mode: fast, balanced, deep")
    parser.add_argument("-p", "--ports", help="ports, e.g. 80,443 or 1-1000")
    parser.add_argument("-M", "--modules", default="safe", help="extra modules: none,dns,dns-deep,passive,web,http,tls,screenshots,templates,safe,all,full,mission")
    parser.add_argument("-A", "--aggressive", action="store_true", help="enable heavier safe checks when tools exist")
    parser.add_argument("-t", "--timeout", type=int, default=90, help="timeout per tool command")
    parser.add_argument("-o", "--json", type=Path, help="save JSON report")
    parser.add_argument("--markdown", "--md", dest="markdown", type=Path, help="save Markdown report")
    parser.add_argument("--html", type=Path, help="save standalone HTML report")
    parser.add_argument("--raw-dir", type=Path, help="save raw tool outputs/artifacts into this directory")
    parser.add_argument("--diff", type=Path, help="compare this scan against a previous JSON report")
    parser.add_argument("--deep", action="store_true", help="alias for -m deep")
    parser.add_argument("--mission", action="store_true", help="enable full mission module set: passive,dns-deep,web,http-detail,tls,screenshots,templates")
    parser.add_argument("--passive", action="store_true", help="add passive subdomain discovery modules")
    parser.add_argument("--http-detail", action="store_true", help="add curl header checks and shallow crawl when tools exist")
    parser.add_argument("--screenshots", action="store_true", help="capture a screenshot with gowitness when installed")
    parser.add_argument("--templates", "--nuclei", dest="templates", action="store_true", help="run nuclei templates when installed and authorized")
    parser.add_argument("--cmd", "--show-commands", dest="show_commands", action="store_true", help="show exact commands")
    parser.add_argument("--explain", action="store_true", help="show switch guide in output")
    parser.add_argument("--no-color", action="store_true", help="disable colors")
    parser.add_argument("--no-whois", action="store_true", help="skip WHOIS")
    parser.add_argument("--install-deps", action="store_true", help="install tools best-effort using apt/dnf/pacman/apk/brew/choco/winget/go/pipx")
    parser.add_argument("--self-install", "--setup", dest="self_install", action="store_true", help="install only the reconkit command into a system/user bin directory")
    parser.add_argument("--user", dest="user_install", action="store_true", help="with --self-install, prefer ~/.local/bin")
    parser.add_argument("--with-optional", action="store_true", help="with --install-deps, also install optional recon/web/TLS tools")
    parser.add_argument("--dry-run", action="store_true", help="with --install-deps, print install commands only")
    parser.add_argument("--check-deps", action="store_true", help="print dependency status and exit")
    parser.add_argument("--ai", action="store_true", help="analyze scan results using recon_config.json AI settings")
    parser.add_argument("--ai-timeout", type=int, default=60, help="AI request timeout")
    parser.add_argument("--ai-out", type=Path, help="save AI analysis to file")
    parser.add_argument("--ai-prompt", action="store_true", help="print configured AI system prompt and exit")
    parser.add_argument("--show-config", action="store_true", help="print loaded AI config without API key and exit")
    parser.add_argument("--test-ai", action="store_true", help="test AI endpoint/model/API key without scanning")
    parser.add_argument("--version", action="store_true", help="show ReconKit version and Team CynetX links")
    return parser.parse_args(argv)

def status(message: str, *, colorize: bool = True) -> None:
    print(color(f"[◆] {message}", C.CYAN, colorize), file=sys.stderr)


def render_home(colorize: bool = True) -> str:
    banner = color(r"""
    ____                       __ __ _ __
   / __ \___  _________  ____ / //_(_) /_
  / /_/ / _ \/ ___/ __ \/ __ \/ ,< / / __/
 / _, _/  __/ /__/ /_/ / / / / /| / / /_
/_/ |_|\___/\___/\____/_/ /_//_/ |_/_/\__/
""".strip("\n"), C.BOLD + C.MAGENTA, colorize)
    header = box([
        color(f"⚡ authorized recon dashboard by {AUTHOR}", C.BOLD + C.CYAN, colorize),
        pill("MODE", "friendly launcher", C.MAGENTA, colorize=colorize),
        pill("RUN", "reconkit <target>", C.GREEN, colorize=colorize),
        pill("TEAM", "cynetx.ir • t.me/cynetx", C.CYAN, colorize=colorize),
        pill("SETUP", "reconkit --install-deps --with-optional", C.YELLOW, colorize=colorize),
    ], title=" ReconKit Home ", accent=C.MAGENTA, colorize=colorize)
    quick_rows = [
        ["Start scan", "reconkit example.com"],
        ["Full mission", "reconkit example.com --mission --raw-dir artifacts -o scan.json --html report.html"],
        ["Install command only", "python3 recon.py --self-install --user"],
        ["Install tools", "reconkit --install-deps --with-optional"],
        ["Check setup", "reconkit --check-deps"],
        ["AI test", "reconkit --test-ai"],
    ]
    tips_rows = [
        ["No target?", "Interactive console opens in a real terminal; this dashboard appears in non-interactive output."],
        ["Safe by design", "No brute-force, exploit payloads, persistence, or destructive actions."],
        ["Reports", "Use -o scan.json --markdown report.md --html report.html"],
    ]
    return "\n".join([
        banner,
        header,
        hr("Quick Actions", colorize=colorize),
        table(["Action", "Command"], quick_rows, colorize=colorize, max_widths=[22, 104]),
        hr("Operator Notes", colorize=colorize),
        table(["Signal", "Meaning"], tips_rows, colorize=colorize, max_widths=[18, 104]),
    ])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    colorize = not args.no_color and sys.stdout.isatty()
    started = time.monotonic()

    if args.version:
        print(f"{APP} v{VERSION} by {AUTHOR}")
        print(f"Website: {WEBSITE}")
        print(f"Telegram: {TELEGRAM}")
        print(COPYRIGHT)
        return 0

    if args.self_install:
        code = install_command_entry(prefer_user=args.user_install, colorize=colorize)
        if code != 0:
            return code
        if not args.install_deps:
            return 0
    if args.check_deps:
        print_dependencies(colorize=colorize)
        return 0
    if args.install_deps:
        return install_deps(args.with_optional, args.dry_run, colorize=colorize)
    if args.ai_prompt or args.show_config or args.test_ai:
        try:
            ai_config = load_config()
            validate_ai_config(ai_config)
        except ValueError as exc:
            print(color(f"Invalid config: {exc}", C.RED, colorize), file=sys.stderr)
            return 2
        if args.ai_prompt:
            print(str(ai_config["system_prompt"]))
            return 0
        if args.show_config:
            print(json.dumps(safe_config_for_display(ai_config), ensure_ascii=False, indent=2))
            return 0
        key = ai_api_key(ai_config)
        if not key:
            print(color(f"AI test failed: API key missing. {ai_key_hint(ai_config)}", C.RED, colorize), file=sys.stderr)
            return 2
        status(f"Testing AI endpoint: {ai_config['endpoint_url']}", colorize=colorize)
        status(f"Testing AI model: {ai_config['model']}", colorize=colorize)
        try:
            reply = test_ai_connection(ai_config, key, args.ai_timeout)
        except RuntimeError as exc:
            print(color(f"AI test failed: {exc}", C.RED, colorize), file=sys.stderr)
            return 1
        print(color("[+] AI endpoint/model/API key test succeeded.", C.GREEN, colorize))
        print(f"Reply: {reply}")
        return 0
    if not args.target:
        if sys.stdin.isatty():
            return run_console(colorize=colorize)
        print(render_home(colorize=colorize))
        return 0

    try:
        target = normalize_target(args.target)
        modules = parse_modules(args.modules)
        if args.mission:
            modules |= parse_modules("mission")
        if args.passive:
            modules |= parse_modules("passive")
        if args.http_detail:
            modules |= parse_modules("http-detail")
        if args.screenshots:
            modules |= parse_modules("screenshots")
        if args.templates:
            modules |= parse_modules("templates")
    except ValueError as exc:
        print(color(f"Invalid input: {exc}", C.RED, colorize), file=sys.stderr)
        return 2

    mode = "deep" if args.deep else args.mode
    report = ReconReport(target=args.target, normalized_target=target, started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), profile=mode)

    status(f"Locking target: {target}", colorize=colorize)
    report.resolved_ips = resolve_target(target)
    if not report.resolved_ips:
        report.notes.append("No IPs resolved through system resolver; this is usually NXDOMAIN, a typo, or a DNS/server issue.")
        report.notes.append("Endpoint scans skipped because there is no IP address to scan. Check spelling/DNS and retry.")
    for ip in report.resolved_ips:
        report.reverse_dns[ip] = reverse_lookup(ip)

    status("Collecting DNS records", colorize=colorize)
    scan_dns(target, max(10, args.timeout), report)

    if target_has_scan_endpoint(report):
        status(f"Launching nmap mode: {mode}", colorize=colorize)
        scan_nmap(target, max(10, args.timeout), report, args.ports, mode == "deep")
    else:
        status("Skipping nmap: target did not resolve to an IP", colorize=colorize)

    if modules:
        status(f"Running extra modules: {','.join(sorted(modules))}", colorize=colorize)
        scan_extra_modules(report, max(10, args.timeout), modules, args.aggressive, args.raw_dir)

    if not args.no_whois:
        status("Pulling WHOIS summary", colorize=colorize)
        scan_whois(target, max(10, args.timeout), report)

    report.elapsed_seconds = time.monotonic() - started
    print(render(report, colorize=colorize, show_commands=args.show_commands, explain=args.explain))

    if args.diff:
        try:
            diff_lines = diff_reports(args.diff, report)
        except (OSError, json.JSONDecodeError) as exc:
            print(color(f"\n[!] Diff failed: {exc}", C.RED, colorize), file=sys.stderr)
        else:
            print(color("\n[+] Diff summary:", C.CYAN, colorize))
            for line in diff_lines:
                print(f"  - {line}")

    if args.json:
        save_json(report, args.json)
        print(color(f"\n[+] JSON report saved: {args.json}", C.GREEN, colorize))
    if args.markdown:
        save_markdown(report, args.markdown)
        print(color(f"[+] Markdown report saved: {args.markdown}", C.GREEN, colorize))
    if args.html:
        save_html(report, args.html)
        print(color(f"[+] HTML report saved: {args.html}", C.GREEN, colorize))

    if args.ai:
        try:
            ai_config = load_config()
            validate_ai_config(ai_config)
        except ValueError as exc:
            print(color(f"\n[!] Invalid AI config: {exc}", C.RED, colorize), file=sys.stderr)
            return 2
        key = ai_api_key(ai_config)
        if not key:
            print(color(f"\n[!] AI API key missing. {ai_key_hint(ai_config)}", C.RED, colorize), file=sys.stderr)
            return 2
        status(f"Requesting AI analysis via {ai_config.get('provider', 'openrouter')} model: {ai_config['model']}", colorize=colorize)
        try:
            ai_text = call_openrouter(report, ai_config, key, args.ai_timeout, colorize=colorize)
        except RuntimeError as exc:
            print(color(f"\n[!] AI analysis failed: {exc}", C.RED, colorize), file=sys.stderr)
            return 1
        print("\n" + render_ai_analysis(ai_text, colorize=colorize))
        if args.ai_out:
            args.ai_out.parent.mkdir(parents=True, exist_ok=True)
            args.ai_out.write_text(ai_text + "\n", encoding="utf-8")
            print(color(f"\n[+] AI analysis saved: {args.ai_out}", C.GREEN, colorize))

    return 0
