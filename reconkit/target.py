import ipaddress
import socket
from urllib.parse import urlparse

from .models import ReconReport

def normalize_target(raw: str) -> str:
    candidate = raw.strip()
    parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
    host = parsed.hostname or candidate.split("/")[0]
    host = host.strip("[]").rstrip(".")
    if not host:
        raise ValueError("empty target")
    return host

def is_ip(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False

def target_has_scan_endpoint(report: ReconReport) -> bool:
    return is_ip(report.normalized_target) or bool(report.resolved_ips)

def resolve_target(target: str) -> list[str]:
    if is_ip(target):
        return [target]
    ips: set[str] = set()
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            for item in socket.getaddrinfo(target, None, family, socket.SOCK_STREAM):
                ips.add(item[4][0])
        except socket.gaierror:
            continue
    return sorted(ips, key=lambda value: (":" in value, value))

def reverse_lookup(ip: str) -> list[str]:
    try:
        names, _, _ = socket.gethostbyaddr(ip)
        return [names]
    except (socket.herror, socket.gaierror):
        return []
