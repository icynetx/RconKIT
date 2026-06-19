# ReconKit

A modular, terminal-friendly reconnaissance dashboard for authorized red-team and defensive exposure reviews.

ReconKit orchestrates local tools safely, normalizes their output, and produces console, JSON, Markdown, HTML, raw-evidence, and AI-assisted reports.


## One-Command Local Setup

Install only the `reconkit` command, without installing external tools:

```bash
python3 recon.py --self-install --user
```

Install the `reconkit` command plus all available tools:

```bash
python3 recon.py --self-install --install-deps --with-optional
```

After that, just run:

```bash
reconkit
reconkit example.com --mission --raw-dir artifacts -o scan.json --html report.html
```

Running `reconkit` with no arguments opens a polished quick-start dashboard instead of throwing an error.

## Quick Start

```bash
reconkit example.com
reconkit example.com --deep --ai --ai-out ai-report.md -o scan.json -t 120
reconkit example.com --mission --raw-dir artifacts -o scan.json --html report.html --markdown report.md
```


## Demo Showcase

> Replace the GIF placeholders below after recording your terminal demos. Keep the filenames in `assets/demos/` and GitHub will render them automatically.

### ⚡ Command Center — Friendly Home Dashboard

<p align="center">
  <img src="assets/demos/home-dashboard.gif" alt="ReconKit home dashboard demo" width="900">
</p>

Open ReconKit with no arguments and get a polished operator dashboard instead of a confusing error. Perfect for first-time users.

```bash
reconkit
```

### 🛰️ Mission Scan — Full Recon Workflow

<p align="center">
  <img src="assets/demos/mission-scan.gif" alt="ReconKit mission scan demo" width="900">
</p>

Run DNS, nmap, web fingerprinting, TLS checks, passive discovery, artifacts, and reporting in one clean command.

```bash
reconkit scanme.nmap.org --mission --no-whois --raw-dir artifacts -o scan.json --markdown report.md --html report.html -t 120
```

### 🧠 AI Analyst — Scan-to-Report Intelligence

<p align="center">
  <img src="assets/demos/ai-analysis.gif" alt="ReconKit AI analysis demo" width="900">
</p>

Send normalized scan evidence to your configured OpenRouter model and get an executive + technical defensive analysis.

```bash
reconkit scanme.nmap.org -M safe --no-whois --ai --ai-out ai-report.md -o ai-scan.json -t 90
```

### 📊 HTML Report — Client-Ready Output

<p align="center">
  <img src="assets/demos/html-report.gif" alt="ReconKit HTML report demo" width="900">
</p>

Generate clean Markdown/HTML reports with the same scan data used by the console dashboard.

```bash
reconkit scanme.nmap.org -M safe --no-whois -o scan.json --markdown report.md --html report.html
python3 -m http.server 8080
```

Open: `http://127.0.0.1:8080/report.html`

### 🧩 One-Command Setup — Install ReconKit + Tooling

<p align="center">
  <img src="assets/demos/install-deps.gif" alt="ReconKit dependency installer demo" width="900">
</p>

Install the `reconkit` command, detect missing tools, install what is available, and auto-handle Go tool paths.

```bash
python3 recon.py --self-install --user
reconkit --install-deps --with-optional --dry-run
reconkit --check-deps
```

### 🔁 Delta Scan — See What Changed

<p align="center">
  <img src="assets/demos/diff-scan.gif" alt="ReconKit diff scan demo" width="900">
</p>

Compare a new scan against an older JSON report to quickly spot new/removed IPs and ports.

```bash
reconkit scanme.nmap.org -M none --no-whois -o old.json
reconkit scanme.nmap.org -M none --no-whois --diff old.json -o new.json
```

## Recording The Demo GIFs

Install recorder tools:

```bash
sudo apt update
sudo apt install -y asciinema
# If `agg` is unavailable in apt, install it from its upstream release or use `asciinema upload`.
```

Record each demo:

```bash
asciinema rec assets/demos/home-dashboard.cast -c "reconkit"
asciinema rec assets/demos/mission-scan.cast -c "reconkit scanme.nmap.org --mission --no-whois --raw-dir artifacts -o scan.json --markdown report.md --html report.html -t 120"
asciinema rec assets/demos/ai-analysis.cast -c "reconkit scanme.nmap.org -M safe --no-whois --ai --ai-out ai-report.md -o ai-scan.json -t 90"
asciinema rec assets/demos/html-report.cast -c "reconkit scanme.nmap.org -M safe --no-whois -o scan.json --markdown report.md --html report.html"
asciinema rec assets/demos/install-deps.cast -c "reconkit --install-deps --with-optional --dry-run"
asciinema rec assets/demos/diff-scan.cast -c "reconkit scanme.nmap.org -M none --no-whois --diff old.json -o new.json"
```

Convert casts to GIFs if `agg` is installed:

```bash
agg assets/demos/home-dashboard.cast assets/demos/home-dashboard.gif
agg assets/demos/mission-scan.cast assets/demos/mission-scan.gif
agg assets/demos/ai-analysis.cast assets/demos/ai-analysis.gif
agg assets/demos/html-report.cast assets/demos/html-report.gif
agg assets/demos/install-deps.cast assets/demos/install-deps.gif
agg assets/demos/diff-scan.cast assets/demos/diff-scan.gif
```

Tips for beautiful recordings:

- Use a wide terminal, around `120x34`.
- Run `reconkit --no-color` only if your GIF renderer has color issues; otherwise keep colors on.
- Clear old outputs first: `rm -rf artifacts scan.json report.md report.html ai-report.md old.json new.json`.
- Use `scanme.nmap.org` for demos because it is intentionally provided for nmap testing.

## Scan Profiles

- `fast`: quick DNS + common-port nmap workflow.
- `balanced`: broader port coverage for common infra/admin services.
- `deep`: nmap service/default-script pass with fallback discovery.

## Module Sets

- `-M safe`: DNS tools, web fingerprinting, TLS checks.
- `-M all`: safe + passive discovery, DNS AXFR validation, HTTP detail.
- `-M full` / `--mission`: all + screenshots + nuclei template checks when installed.
- `-M none`: core DNS + nmap only.

Individual modules:

```bash
-M dns
-M dns-deep
-M passive
-M web
-M http
-M tls
-M screenshots
-M templates
```

## Useful Examples

```bash
reconkit example.com --check-deps
reconkit --install-deps --with-optional --dry-run
reconkit example.com -p 80,443,2083,2096 --cmd
reconkit example.com -M web,tls,http-detail -t 120
reconkit example.com --passive --raw-dir artifacts
reconkit example.com --mission --raw-dir artifacts -o scan.json --html report.html
reconkit example.com --diff previous-scan.json -o new-scan.json
reconkit --test-ai
```


## Installing Tools

ReconKit has a best-effort installer. It detects common package managers and installs what is available without failing the whole run because one optional tool is unavailable.

Supported installers/providers:

- Linux: `apt`, `dnf`, `pacman`, `apk`
- macOS: `brew`
- Windows: `winget`, `choco`
- Fallbacks: `go install`, `pipx`, `python3 -m pip --user`

Dry-run first:

```bash
reconkit --install-deps --with-optional --dry-run
```

Install required tools only:

```bash
reconkit --install-deps
```

Install required + optional recon tooling:

```bash
reconkit --install-deps --with-optional
```

Notes:

- Some tools are not packaged on every OS. ReconKit prints manual install hints instead of crashing.
- On Windows, some DNS/web tools are easier through WSL/Kali or Git Bash.
- For ProjectDiscovery tools installed via Go, ensure `~/go/bin` or `%USERPROFILE%\go\bin` is in `PATH`.

## Optional Tools

ReconKit uses tools only when installed and skips missing tools cleanly:

- Core: `nmap`, `dig`, `host`, `nslookup`, `whois`
- Web/TLS: `whatweb`, `httpx`/`httpx-toolkit`, `wafw00f`, `sslscan`, `testssl.sh`, `curl`
- Passive/HTTP: `subfinder`, `amass`, `katana`, `gowitness`
- Template checks: `nuclei`
- Reporting helpers: `jq`

## Reports

- JSON: `-o scan.json`
- Markdown: `--markdown report.md`
- HTML: `--html report.html`
- Raw evidence: `--raw-dir artifacts`
- Diff: `--diff old-scan.json`

## AI Configuration

AI settings are loaded from `recon_config.json`. Keep API keys private and avoid sharing scan reports that include sensitive infrastructure details.

## Scope and Safety

ReconKit is designed for authorized reconnaissance only. It does not run brute force, exploit payloads, credential attacks, persistence, evasion, malware, or destructive actions. Only scan systems you own or have explicit permission to test.
