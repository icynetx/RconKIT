import re

from .constants import DEFAULT_RECORDS

def parse_dig_answer(output: str) -> list[str]:
    records = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split()
        if len(parts) >= 5 and parts[3] in DEFAULT_RECORDS:
            records.append(" ".join(parts[3:]))
        elif len(parts) >= 1:
            records.append(line)
    return records

def parse_nmap(output: str) -> list[dict[str, str]]:
    ports = []
    in_ports = False
    for line in output.splitlines():
        if line.startswith("PORT"):
            in_ports = True
            continue
        if not in_ports:
            continue
        if not line.strip() or line.startswith(("Service detection", "Nmap done")):
            break
        match = re.match(r"^(\d+/(?:tcp|udp))\s+(open|closed|filtered|unfiltered|open\|filtered|closed\|filtered)\s+(\S+)(?:\s+(.*))?$", line.strip())
        if match:
            ports.append({"port": match.group(1), "state": match.group(2), "service": match.group(3), "version": match.group(4) or ""})
    return ports

def first_lines(output: str, limit: int = 8) -> list[str]:
    lines = []
    for line in output.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if clean and clean not in lines:
            lines.append(clean)
        if len(lines) >= limit:
            break
    return lines

def summarize_host(output: str) -> list[str]:
    keep = []
    for line in output.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or clean.startswith(("Trying", ";;")):
            continue
        if any(token in clean for token in (" has address ", " mail is handled by ", " name server ", " descriptive text ", " SOA ")):
            keep.append(clean)
    return keep[:8] or first_lines(output, 4)

def summarize_nslookup(output: str, stderr: str = "") -> list[str]:
    source = output or stderr
    keep = []
    for line in source.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or clean.startswith(("Server:", "Address:", "Non-authoritative")):
            continue
        if "timed out" in clean or "no servers" in clean:
            keep.append(clean)
        elif any(token in clean.lower() for token in ("name", "address", "mail exchanger", "nameserver", "text")):
            keep.append(clean)
    return keep[:6] or first_lines(source, 4)

def summarize_whatweb(output: str) -> list[str]:
    rows = []
    for line in output.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean:
            continue
        url = clean.split(" ", 1)[0]
        status = re.search(r"\[(\d{3} [^\]]+)\]", clean)
        title = re.search(r"Title\[([^\]]+)\]", clean)
        redirect = re.search(r"RedirectLocation\[([^\]]+)\]", clean)
        headers = []
        for token in ("Strict-Transport-Security", "X-Frame-Options", "Content-Security-Policy", "IP"):
            if token in clean:
                headers.append(token)
        parts = [url]
        if status:
            parts.append(status.group(1))
        if title:
            parts.append("Title=" + title.group(1).replace("[Title element contains newline(s)!", "").strip())
        if redirect:
            parts.append("Redirect=" + redirect.group(1))
        if headers:
            parts.append("Signals=" + ",".join(headers[:4]))
        rows.append(" | ".join(parts))
    return list(dict.fromkeys(rows))[:5] or first_lines(output, 4)

def summarize_wafw00f(output: str) -> list[str]:
    keep = []
    for line in output.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or set(clean) <= {"_", "-", "|", "/", "\\", "(", ")", " ", ".", ","}:
            continue
        lower = clean.lower()
        if "is behind" in lower or "seems to be behind" in lower or "no waf" in lower or "generic detection" in lower:
            keep.append(clean)
        elif "identified" in lower or "detected" in lower:
            keep.append(clean)
    return list(dict.fromkeys(keep))[:4] or ["No clear WAF fingerprint in summarized output."]

def summarize_nikto(output: str) -> list[str]:
    keep = []
    for line in output.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if clean.startswith("+") and not clean.startswith("+ Target"):
            keep.append(clean)
    return keep[:8] or first_lines(output, 4)

def whois_summary(output: str) -> list[str]:
    wanted = (
        "Registrar:", "Registrant Organization:", "Creation Date:", "Updated Date:",
        "Registry Expiry Date:", "Name Server:", "OrgName:", "NetRange:", "CIDR:", "Country:",
    )
    found = []
    seen = set()
    for line in output.splitlines():
        clean = line.strip()
        if not clean or clean.startswith(("%", "#")):
            continue
        if any(clean.lower().startswith(key.lower()) for key in wanted) and clean not in seen:
            found.append(clean)
            seen.add(clean)
        if len(found) >= 12:
            break
    return found
