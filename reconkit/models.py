from dataclasses import dataclass, field


@dataclass
class CmdResult:
    command: list[str]
    ok: bool
    stdout: str = ""
    stderr: str = ""
    elapsed: float = 0.0
    missing: bool = False


@dataclass
class ExtraResult:
    module: str
    tool: str
    ok: bool
    summary: list[str] = field(default_factory=list)
    missing: bool = False
    elapsed: float = 0.0


@dataclass
class Finding:
    title: str
    severity: str
    evidence: str
    recommendation: str
    confidence: str = "medium"




@dataclass
class ReconReport:
    target: str
    normalized_target: str
    started_at: str
    profile: str
    resolved_ips: list[str] = field(default_factory=list)
    reverse_dns: dict[str, list[str]] = field(default_factory=dict)
    dns_records: dict[str, list[str]] = field(default_factory=dict)
    nmap_ports: list[dict[str, str]] = field(default_factory=list)
    whois_summary: list[str] = field(default_factory=list)
    extras: list[ExtraResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    commands: list[dict[str, object]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
