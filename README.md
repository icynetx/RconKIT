<p align="center">
  <img src="assets/reconkit-logo.jpg" alt="ReconKit">
</p>

<h1 align="center">ReconKit ⚡</h1>

<p align="center">
  <b>Turn messy recon tools into a clean command center — fast scans, beautiful reports, and AI-assisted defensive insight from one friendly console.</b>
</p>

<p align="center">
  <a href="https://cynetx.ir">
    <img alt="Website" src="https://img.shields.io/badge/Website-cynetx.ir-00E5FF?style=for-the-badge&logo=googlechrome&logoColor=white">
  </a>
  <a href="https://t.me/cynetx">
    <img alt="Telegram" src="https://img.shields.io/badge/Telegram-@cynetx-26A5E4?style=for-the-badge&logo=telegram&logoColor=white">
  </a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/Linux%20%7C%20macOS%20%7C%20Windows-supported-00c853?style=for-the-badge&logo=windows&logoColor=white">
  <img alt="AI" src="https://img.shields.io/badge/OpenRouter-AI%20Analyst-7C3AED?style=for-the-badge&logo=openai&logoColor=white">
  <img alt="Safety" src="https://img.shields.io/badge/Authorized%20Recon-Only-ff9800?style=for-the-badge&logo=hackthebox&logoColor=white">
</p>

<p align="center">
  <code>nmap</code> • <code>dig</code> • <code>whatweb</code> • <code>httpx</code> • <code>sslscan</code> • <code>subfinder</code> • <code>nuclei</code> • <code>OpenRouter AI</code>
</p>

---

## ✨ What Is ReconKit?

ReconKit is a practical recon workspace for people who want results, not chaos. Give it a domain or IP, and it brings together tools like `nmap`, `dig`, `whatweb`, `httpx`, `sslscan`, `nuclei`, and more — then turns the output into clean tables, useful notes, reports, and optional AI analysis.

It feels like a small command center: beginners can use the guided console, while experienced operators can still run direct one-shot commands and export everything for reports.

ReconKit is made for:

- Red-team operators who need fast authorized external recon.
- Blue-team engineers checking what is exposed to the internet.
- Students and beginners who want a clear workflow instead of random commands.
- Consultants who need clean JSON, Markdown, HTML, raw evidence, and AI-assisted summaries.

> **Safety note:** ReconKit is for assets you own or have explicit permission to test. It does not run brute force, exploit payloads, malware, persistence, evasion, or destructive actions.

---

## 🚀 Highlights

- 🕹️ **Console-first workflow**: run `reconkit` and work with simple commands like `set target`, `show options`, `run`, and `mission`.
- 🛰️ **Real recon tools, cleaner experience**: DNS, nmap, WHOIS, web fingerprinting, TLS checks, passive discovery, screenshots, and template checks.
- 🧠 **AI analyst mode**: send normalized scan evidence to OpenRouter and get a clear defensive analysis in English.
- 📊 **Reports without the mess**: export console output, JSON, Markdown, HTML, raw artifacts, and scan diffs.
- 🧩 **Installer that tries to help**: uses native package managers and Go/Python fallbacks where possible.
- 🪟 **Windows-aware**: creates native launchers, updates user PATH, and keeps running even when optional Unix tools are unavailable.
- 🧼 **Human-readable output**: aligned tables, wrapped columns, quick-take notes, and practical next steps.

---

## 📸 See It In Action

GitHub renders these GIFs inline, and in most browsers they autoplay automatically. They are intentionally short so visitors can understand the workflow in a few seconds without reading the whole README.

<table>
  <tr>
    <td width="50%" align="center">
      <h3>⚡ Guided Console</h3>
      <img src="assets/demos/home-dashboard.gif" alt="ReconKit guided console demo" width="100%">
      <br>
      <sub>Open ReconKit like a command center and start with simple console commands.</sub>
      <br><br>
      <code>reconkit</code>
    </td>
    <td width="50%" align="center">
      <h3>🛰️ Full Mission Scan</h3>
      <img src="assets/demos/mission-scan.gif" alt="ReconKit mission scan demo" width="100%">
      <br>
      <sub>Run DNS, nmap, web, TLS, passive modules, artifacts, and reports in one flow.</sub>
      <br><br>
      <code>reconkit scanme.nmap.org --mission --no-whois --raw-dir artifacts -o scan.json --markdown report.md --html report.html -t 120</code>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <h3>🧠 AI-Assisted Analysis</h3>
      <img src="assets/demos/ai-analysis.gif" alt="ReconKit AI analysis demo" width="100%">
      <br>
      <sub>Turn normalized scan evidence into a clear defensive analysis with OpenRouter.</sub>
      <br><br>
      <code>reconkit scanme.nmap.org -M safe --no-whois --ai --ai-out ai-report.md -o ai-scan.json -t 90</code>
    </td>
    <td width="50%" align="center">
      <h3>📊 Clean HTML Report</h3>
      <img src="assets/demos/html-report.gif" alt="ReconKit HTML report demo" width="100%">
      <br>
      <sub>Export Markdown and HTML reports that are easy to share and review.</sub>
      <br><br>
      <code>reconkit scanme.nmap.org -M safe --no-whois -o scan.json --markdown report.md --html report.html</code>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <h3>🧩 Dependency Installer</h3>
      <img src="assets/demos/install-deps.gif" alt="ReconKit dependency installer demo" width="100%">
      <br>
      <sub>Preview or install required and optional tools without memorizing package names.</sub>
      <br><br>
      <code>reconkit --install-deps --with-optional --dry-run</code>
    </td>
    <td width="50%" align="center">
      <h3>🔁 Delta Scan</h3>
      <img src="assets/demos/diff-scan.gif" alt="ReconKit diff scan demo" width="100%">
      <br>
      <sub>Compare scans and quickly spot changes in IPs, ports, and exposure.</sub>
      <br><br>
      <code>reconkit scanme.nmap.org -M none --no-whois --diff old.json -o new.json</code>
    </td>
  </tr>
</table>

> Six demos are included on purpose: console, mission scan, AI analysis, report export, dependency setup, and scan diff. That is enough to show the full workflow without making the README heavy.


## ⚡ Quick Start

### 1) Install the `reconkit` command

```bash
python3 recon.py --self-install --user
```

### 2) Open your recon console

```bash
reconkit
```

From there, work naturally:

```text
reconkit(no-target)> help
reconkit(no-target)> set target example.com
reconkit(example.com)> set mode balanced
reconkit(example.com)> set modules mission
reconkit(example.com)> enable no_whois
reconkit(example.com)> run
reconkit(example.com)> exit
```

### 3) Prefer direct commands? Use one-shot mode

```bash
reconkit example.com
reconkit example.com --deep --ai --ai-out ai-report.md -o scan.json -t 120
reconkit example.com --mission --raw-dir artifacts -o scan.json --markdown report.md --html report.html
```

---

## 🧭 Interactive Console Guide

Run `reconkit` with no arguments and you get a guided console instead of a wall of flags. Set your target once, adjust the scan style, and run whenever you are ready.

| Command | What it does |
|---|---|
| `help` or `?` | Shows console commands. |
| `show options` | Shows current target, profile, modules, report paths, and flags. |
| `show modules` | Shows module presets. |
| `show deps` | Prints dependency status. |
| `set target example.com` | Sets the target domain, IP, or URL. |
| `set mode fast` | Sets scan mode: `fast`, `balanced`, or `deep`. |
| `set modules mission` | Sets module preset or comma-separated modules. |
| `set ports 80,443,8080` | Uses custom ports. |
| `unset ports` | Clears custom ports and returns to defaults. |
| `set timeout 120` | Sets per-tool timeout in seconds. |
| `set raw_dir artifacts` | Sets raw artifact output directory. |
| `set json scan.json` | Sets JSON output path. |
| `set markdown report.md` | Sets Markdown output path. |
| `set html report.html` | Sets HTML output path. |
| `enable ai` / `disable ai` | Enables/disables AI analysis. |
| `enable aggressive` | Enables heavier safe checks when tools exist. |
| `enable no_whois` | Skips WHOIS. |
| `enable show_commands` | Shows exact tool commands in output. |
| `run` or `scan` | Runs the scan using current options. |
| `quick example.com` | Runs a fast safe scan immediately. |
| `mission example.com` | Runs the full mission workflow. |
| `install` | Installs required + optional tools best-effort. |
| `dryrun` | Shows dependency install plan without installing. |
| `test ai` | Tests OpenRouter endpoint/model/API key. |
| `shell <command>` | Runs a local shell command. |
| `clear` | Clears the screen and redraws the console banner. |
| `exit`, `quit`, `q` | Leaves the console. |

---

## 🛠️ Installation

The fastest way is the one-command installer. It clones ReconKit, installs the `reconkit` command for your user, then installs available tools best-effort.

### Linux / macOS — one command

```bash
curl -fsSL https://raw.githubusercontent.com/icynetx/RconKIT/main/scripts/install.sh | sh
```

If you only want the ReconKit command and do **not** want external tools installed automatically:

```bash
curl -fsSL https://raw.githubusercontent.com/icynetx/RconKIT/main/scripts/install.sh | RECONKIT_SKIP_TOOLS=1 sh
```

If you want required tools only, without optional tools:

```bash
curl -fsSL https://raw.githubusercontent.com/icynetx/RconKIT/main/scripts/install.sh | RECONKIT_INSTALL_OPTIONAL=0 sh
```

### Windows PowerShell — one command

```powershell
iwr -useb https://raw.githubusercontent.com/icynetx/RconKIT/main/scripts/install.ps1 | iex
```

Command only, without external tools:

```powershell
$env:RECONKIT_SKIP_TOOLS="1"; iwr -useb https://raw.githubusercontent.com/icynetx/RconKIT/main/scripts/install.ps1 | iex
```

Required tools only:

```powershell
$env:RECONKIT_INSTALL_OPTIONAL="0"; iwr -useb https://raw.githubusercontent.com/icynetx/RconKIT/main/scripts/install.ps1 | iex
```

After installation, open a new terminal if needed:

```bash
reconkit
reconkit --check-deps
reconkit scanme.nmap.org -M safe --no-whois -t 90
```

### Local/manual install from a cloned repo

Use this when you already downloaded the project manually.

```bash
python3 recon.py --self-install --user
reconkit --install-deps --with-optional
reconkit --check-deps
```

Windows local install:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\install-windows.ps1
```

Windows CMD local install:

```cmd
scripts\install-windows.cmd
```

### Supported systems

| System | Recommended install |
|---|---|
| Kali / Ubuntu / Debian | `curl -fsSL .../scripts/install.sh \| sh` |
| Fedora / RHEL-like | `curl -fsSL .../scripts/install.sh \| sh` |
| Arch Linux | `curl -fsSL .../scripts/install.sh \| sh` |
| Alpine Linux | `curl -fsSL .../scripts/install.sh \| sh` |
| macOS | `curl -fsSL .../scripts/install.sh \| sh` |
| Windows PowerShell | `iwr -useb .../scripts/install.ps1 \| iex` |

> On Windows, `dig` and `host` are treated as optional because they are Unix/BIND-style tools. ReconKit uses a Python DNS fallback for basic A/AAAA resolution if they are missing.


## 📦 Dependency Installer

ReconKit checks what is already installed, detects your package manager, and builds a best-effort install plan. If an optional tool is not available on your OS, it tells you clearly and keeps working.

| Platform | Providers |
|---|---|
| Debian/Ubuntu/Kali | `apt` |
| Fedora/RHEL-like | `dnf` |
| Arch | `pacman` |
| Alpine | `apk` |
| macOS | `brew` |
| Windows | `winget`, `choco` |
| Cross-platform fallback | `go install`, `pipx`, `python -m pip --user` |

Preview install commands:

```bash
reconkit --install-deps --with-optional --dry-run
```

Install required tools only:

```bash
reconkit --install-deps
```

Install required + optional tools:

```bash
reconkit --install-deps --with-optional
```

Check status:

```bash
reconkit --check-deps
```

### Tools ReconKit Can Use

| Category | Tools |
|---|---|
| Core | `nmap`, `dig`, `host`, `nslookup`, `whois` |
| Web fingerprinting | `whatweb`, `httpx` / `httpx-toolkit`, `curl` |
| WAF/TLS | `wafw00f`, `sslscan`, `testssl.sh` |
| Passive discovery | `subfinder`, `amass` |
| HTTP crawling/screenshots | `katana`, `gowitness` |
| Template checks | `nuclei` |
| Reporting helper | `jq` |

Optional tools are useful, but not mandatory. If one is missing, ReconKit reports it and continues instead of breaking your scan.

---

## 🔍 Scan Modes

| Mode | Command | Use when |
|---|---|---|
| `fast` | `reconkit example.com` | You want quick DNS + common-port nmap results. |
| `balanced` | `reconkit example.com -m balanced` | You want broader common service coverage. |
| `deep` | `reconkit example.com -m deep` or `--deep` | You want nmap service/version/default-script detection with fallback discovery. |

---

## 🧩 Modules

Use `-M` / `--modules` to decide how much ReconKit should do beyond the core DNS + nmap workflow.

| Module | What it runs |
|---|---|
| `none` | Core DNS + nmap only. |
| `dns` / `dns-tools` | `host`, `nslookup` summaries. |
| `dns-deep` | Safe DNS AXFR validation with `dig axfr`. |
| `passive` / `subdomains` | Passive discovery with `subfinder` and `amass` when installed. |
| `web` | Web fingerprinting with `whatweb`, `httpx`, and WAF check with `wafw00f`. |
| `http` | `web` + HTTP header checks and shallow crawl. |
| `http-detail` | `curl` headers and `katana` shallow crawl when installed. |
| `tls` / `ssl` | TLS checks with `sslscan` or `testssl.sh`. |
| `screenshots` / `shots` | Web screenshot with `gowitness`. |
| `templates` / `nuclei` | Safe nuclei template checks when installed. |
| `safe` | `dns-tools`, `web`, `tls`. Default. |
| `all` | `safe`, `passive`, `dns-deep`, `http-detail`. |
| `full` | `all`, `screenshots`, `templates`. |
| `mission` | Same as `full`; designed for full workflow scans. |

Examples:

```bash
reconkit example.com -M none
reconkit example.com -M web,tls,http-detail
reconkit example.com -M passive,dns-deep
reconkit example.com --mission
```

---

## 🧾 All CLI Switches

| Switch | Example | Explanation |
|---|---|---|
| `target` | `reconkit example.com` | Domain, IP, or URL to scan. |
| `-h`, `--help` | `reconkit --help` | Show help and examples. |
| `-m`, `--mode`, `--profile` | `-m balanced` | Scan mode: `fast`, `balanced`, `deep`. |
| `-p`, `--ports` | `-p 80,443,8080` | Custom nmap ports/ranges. |
| `-M`, `--modules` | `-M web,tls` | Extra modules or presets. |
| `-A`, `--aggressive` | `-A` | Enables heavier safe checks when tools exist, such as `nikto`/`testssl.sh`. |
| `-t`, `--timeout` | `-t 120` | Per-tool command timeout in seconds. |
| `-o`, `--json` | `-o scan.json` | Save normalized JSON report. |
| `--markdown`, `--md` | `--markdown report.md` | Save Markdown report. |
| `--html` | `--html report.html` | Save standalone HTML report. |
| `--raw-dir` | `--raw-dir artifacts` | Save raw tool outputs/artifacts. |
| `--diff` | `--diff old.json` | Compare current scan with previous JSON. |
| `--deep` | `--deep` | Alias for `-m deep`. |
| `--mission` | `--mission` | Enables the full mission module set. |
| `--passive` | `--passive` | Adds passive subdomain discovery modules. |
| `--http-detail` | `--http-detail` | Adds HTTP headers and shallow crawl. |
| `--screenshots` | `--screenshots` | Captures screenshot with `gowitness` when installed. |
| `--templates`, `--nuclei` | `--templates` | Runs nuclei templates when installed and authorized. |
| `--cmd`, `--show-commands` | `--cmd` | Shows exact commands ReconKit executed. |
| `--explain` | `--explain` | Shows a switch guide in the scan output. |
| `--no-color` | `--no-color` | Disables ANSI colors. Useful for CI/log files. |
| `--no-whois` | `--no-whois` | Skips WHOIS lookup. |
| `--install-deps` | `--install-deps` | Installs required tools best-effort. |
| `--self-install`, `--setup` | `--self-install --user` | Installs the `reconkit` command. |
| `--user` | `--self-install --user` | Prefer user bin directory such as `~/.local/bin` or `%USERPROFILE%\.reconkit\bin`. |
| `--with-optional` | `--install-deps --with-optional` | Also install optional recon/web/TLS tools. |
| `--dry-run` | `--install-deps --dry-run` | Print install plan without installing. |
| `--check-deps` | `--check-deps` | Print dependency status and exit. |
| `--ai` | `--ai` | Analyze scan results using `recon_config.json`. |
| `--ai-timeout` | `--ai-timeout 90` | AI request timeout in seconds. |
| `--ai-out` | `--ai-out ai-report.md` | Save AI analysis to a file. |
| `--ai-prompt` | `--ai-prompt` | Print configured AI system prompt and exit. |
| `--show-config` | `--show-config` | Print loaded AI config without exposing the full API key. |
| `--test-ai` | `--test-ai` | Test AI endpoint/model/API key without scanning. |
| `--version` | `--version` | Show ReconKit version and Team CynetX links. |

---

## 🧠 AI Analysis With OpenRouter

ReconKit reads AI settings from `recon_config.json`, so you do not need to pass your model, endpoint, or prompt every time.

Example config:

```json
{
  "provider": "openrouter",
  "endpoint_url": "https://openrouter.ai/api/v1/chat/completions",
  "model": "openrouter/free",
  "api_key_env": "OPENROUTER_API_KEY",
  "api_key": "",
  "temperature": 0.15,
  "max_tokens": 5000,
  "continuation_rounds": 5,
  "empty_response_retries": 5,
  "retry_delay_seconds": 3,
  "http_referer": "https://local.reconkit",
  "x_title": "ReconKit AI Analysis"
}
```

Recommended API key usage:

```bash
export OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY"
reconkit --test-ai
reconkit example.com --deep --ai --ai-out ai-report.md -o scan.json
```

AI output structure:

1. Executive Summary
2. Attack Surface Table
3. Risk Assessment
4. How an Attacker Might Abuse This (Defensive View)
5. Recommended Next Authorized Tests
6. Defensive Hardening Plan
7. Top 5 Priorities
8. Data Quality Notes

> The AI mode is designed for defensive analysis: it explains exposure, likely risk, safe validation ideas, and hardening steps — without exploit payloads, brute-force instructions, malware, persistence, or evasion.

---

## 📊 Reports And Artifacts

| Output | Command | Result |
|---|---|---|
| Console | `reconkit example.com` | Pretty terminal dashboard. |
| JSON | `-o scan.json` | Machine-readable normalized data. |
| Markdown | `--markdown report.md` | GitHub/client-friendly report. |
| HTML | `--html report.html` | Standalone HTML report. |
| Raw evidence | `--raw-dir artifacts` | Tool outputs and artifacts. |
| Diff | `--diff old.json` | Highlights changes from a previous scan. |
| AI report | `--ai-out ai-report.md` | Saved AI analysis. |

A complete report workflow can look like this:

```bash
reconkit example.com --mission --raw-dir artifacts -o scan.json --markdown report.md --html report.html --ai --ai-out ai-report.md -t 120
```

---

## 🧯 Troubleshooting

| Problem | Fix |
|---|---|
| `reconkit: command not found` | Run `python3 recon.py --self-install --user`, then open a new terminal. |
| `Permission denied` from old launcher | Remove the broken old launcher earlier in `PATH`, then self-install again. |
| `httpx` missing on Ubuntu | Run `reconkit --install-deps --with-optional`; ReconKit uses `go install` fallback. |
| `amass` unavailable in `apt` | This is normal on many distros; ReconKit uses fallback/manual notes. |
| Windows cannot see new Go tools | Open a new PowerShell/CMD after install. |
| AI says empty/no content | Use `--test-ai`, verify `recon_config.json`, API key, model, and OpenRouter account limits. |
| DNS tools missing on Windows | ReconKit falls back to Python A/AAAA resolution; use WSL/Kali for full BIND tools. |

---

## ✅ Example Workflows

### Fast exposure check

```bash
reconkit example.com -M safe --no-whois
```

### Deep scan with reports

```bash
reconkit example.com --deep -A --raw-dir artifacts -o scan.json --markdown report.md --html report.html -t 180
```

### Web/TLS focus

```bash
reconkit example.com -p 80,443,8080,8443,2083,2096 -M web,tls,http-detail --cmd
```

### Passive + DNS validation

```bash
reconkit example.com -M passive,dns-deep --raw-dir artifacts
```

### Compare changes

```bash
reconkit example.com -M none --no-whois -o old.json
reconkit example.com -M none --no-whois --diff old.json -o new.json
```

### AI-assisted defensive report

```bash
reconkit example.com --mission --ai --ai-out ai-report.md -o scan.json --html report.html -t 120
```

---

## 🛡️ Scope And Ethics

ReconKit is built to help defenders and authorized operators understand exposure clearly. Keep it professional: scan only assets you own, manage, or have written permission to test.

By design, ReconKit avoids:

- Brute force and password spraying.
- Exploit payloads and weaponized PoCs.
- Malware, persistence, evasion, or destructive actions.
- Unauthorized access attempts.

---

## 👥 Team CynetX

Built with ❤️ by **Team CynetX** for operators who care about clean recon, readable reports, and practical security work.

© 2026 Team CynetX. All rights reserved.

- Website: https://cynetx.ir
- Telegram: https://t.me/cynetx

If ReconKit makes your workflow cleaner, give the repository a star and share it with someone who still reads raw tool output by hand.
