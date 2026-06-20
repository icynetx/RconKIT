from pathlib import Path

APP = "ReconKit"
VERSION = "2.3"
AUTHOR = "Team CynetX"
WEBSITE = "https://cynetx.ir"
TELEGRAM = "https://t.me/cynetx"
TAGLINE = "beautiful authorized recon console"
COPYRIGHT = "Copyright (c) 2026 Team CynetX. All rights reserved."
DEFAULT_RECORDS = ("A", "AAAA", "MX", "NS", "TXT", "SOA", "CAA")
WEB_FALLBACK_PORTS = "80,443,8080,8443"
FAST_PORTS = "21,22,25,53,80,110,143,443,465,587,993,995,2082,2083,2086,2087,2095,2096,3306,3389,5432,6379,8080,8443,8888"
BALANCED_PORTS = FAST_PORTS + ",81,111,135,139,445,1433,1521,1723,2049,27017,5000,5601,5900,8000,8008,9000,9200,9300"
PROFILE_PORTS = {"fast": FAST_PORTS, "balanced": BALANCED_PORTS}
NMAP_TIMING_ARGS = ("-T4", "--max-retries", "2", "--host-timeout", "75s")
WEB_SERVICES = {"http", "https", "http-alt", "http-proxy", "ssl/http", "sun-answerbook", "radsec", "infowave"}
WEB_PORTS = {"80", "81", "443", "8000", "8008", "8080", "8443", "8888", "2082", "2083", "2086", "2087", "2095", "2096"}
REQUIRED_TOOLS = ("nmap", "dig", "host", "nslookup", "whois")
OPTIONAL_TOOLS = (
    "whatweb", "wafw00f", "sslscan", "nikto", "httpx", "httpx-toolkit", "testssl.sh",
    "subfinder", "amass", "dnsx", "katana", "gowitness", "nuclei", "curl", "jq",
)
CONFIG_PATH = Path(__file__).resolve().parent.parent / "recon_config.json"
PRESETS_PATH = Path(__file__).resolve().parent.parent / "recon_presets.json"
DEFAULT_AI_CONFIG = {
    "provider": "openrouter",
    "endpoint_url": "https://openrouter.ai/api/v1/chat/completions",
    "model": "openai/gpt-4o-mini",
    "temperature": 0.2,
    "max_tokens": 3200,
    "continuation_rounds": 3,
    "empty_response_retries": 3,
    "retry_delay_seconds": 2,
    "http_referer": "https://local.reconkit",
    "x_title": "ReconKit AI Analysis",
    "api_key_env": "OPENROUTER_API_KEY",
    "api_key": "",
    "system_prompt": """You are ReconKit AI, a senior defensive security analyst. Analyze only the authorized reconnaissance data provided by the user.
Rules:
- Do not invent facts, CVEs, ports, technologies, or vulnerabilities not present in the scan data.
- Do not provide exploit steps, weaponized payloads, credential attacks, evasion, persistence, or destructive instructions.
- Keep the answer practical, simple, and prioritized.
- If a tool failed or data is missing, clearly say what is unknown and suggest safe validation steps.
- Answer in professional English unless the user explicitly requests another language.
Required structure:
1) Executive Summary
2) Attack Surface Table
3) Risk Assessment
4) How an Attacker Might Abuse This (Defensive View)
5) Recommended Next Authorized Tests
6) Defensive Hardening Plan
7) Top 5 Priorities
8) Data Quality Notes""",
}
TOOL_PACKAGES = {
    "apt": {"nmap": "nmap", "dig": "dnsutils", "host": "bind9-host", "nslookup": "dnsutils", "whois": "whois", "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto", "httpx": None, "httpx-toolkit": None, "testssl.sh": None, "subfinder": None, "amass": "amass", "dnsx": None, "katana": None, "gowitness": None, "nuclei": None, "curl": "curl", "jq": "jq"},
    "dnf": {"nmap": "nmap", "dig": "bind-utils", "host": "bind-utils", "nslookup": "bind-utils", "whois": "whois", "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto", "httpx": "golang-github-projectdiscovery-httpx", "httpx-toolkit": "golang-github-projectdiscovery-httpx", "testssl.sh": "testssl", "subfinder": None, "amass": "amass", "dnsx": None, "katana": None, "gowitness": None, "nuclei": None, "curl": "curl", "jq": "jq"},
    "pacman": {"nmap": "nmap", "dig": "bind", "host": "bind", "nslookup": "bind", "whois": "whois", "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto", "httpx": "httpx", "httpx-toolkit": "httpx", "testssl.sh": "testssl.sh", "subfinder": "subfinder", "amass": "amass", "dnsx": "dnsx", "katana": "katana", "gowitness": "gowitness", "nuclei": "nuclei", "curl": "curl", "jq": "jq"},
    "apk": {"nmap": "nmap", "dig": "bind-tools", "host": "bind-tools", "nslookup": "bind-tools", "whois": "whois", "whatweb": "whatweb", "wafw00f": "wafw00f", "sslscan": "sslscan", "nikto": "nikto", "httpx": "httpx", "httpx-toolkit": "httpx", "testssl.sh": "testssl", "subfinder": None, "amass": "amass", "dnsx": None, "katana": None, "gowitness": None, "nuclei": None, "curl": "curl", "jq": "jq"},
}
SERVICE_HINTS = {
    "ftp": "FTP exposed; prefer SFTP/SSH and disable anonymous login.",
    "ssh": "SSH visible; enforce keys, rate limits, and no password auth if possible.",
    "smtp": "Mail service visible; check relay policy, SPF/DKIM/DMARC.",
    "domain": "DNS service visible; verify recursion and zone-transfer restrictions.",
    "http": "HTTP visible; check redirects, headers, tech stack, and admin panels.",
    "https": "HTTPS visible; verify TLS, certificates, HSTS, and weak ciphers.",
    "mysql": "Database port visible; restrict by firewall/VPN and strong auth.",
    "postgresql": "Database port visible; restrict by firewall/VPN and strong auth.",
    "redis": "Redis visible; should not be internet-exposed without strict controls.",
    "ms-wbt-server": "RDP visible; protect with VPN/MFA and lockout policy.",
    "microsoft-ds": "SMB visible; risky on internet-facing hosts, restrict exposure.",
}
BANNER = r"""
   ____                         __ __ _ __ 
  / __ \___  _________  ____   / //_(_) /_
 / /_/ / _ \/ ___/ __ \/ __ \ / ,< / / __/
/ _, _/  __/ /__/ /_/ / / / // /| / / /_  
/_/ |_|\___/\___/\____/_/ /_//_/ |_/_/\__/ 
""".strip("\n")
