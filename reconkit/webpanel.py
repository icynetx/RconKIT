"""ReconKit local web panel.

No external Python web framework is required. The panel uses Python's stdlib
ThreadingHTTPServer and exposes local-first APIs for scans, reports, presets,
dependencies, and AI configuration.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import urllib.parse
import uuid
import html
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .ai import ai_api_key, ai_key_hint, apply_ai_config_updates, call_openrouter, load_config, safe_config_for_display, save_config, test_ai_connection, validate_ai_config
from .constants import APP, AUTHOR, TELEGRAM, VERSION, WEBSITE
from .deps import dependency_rows, install_deps
from .models import ExtraResult, Finding, ReconReport
from .presets import create_preset, delete_preset, list_preset_rows, preset_exists, preset_strategy, preset_tool_args, validate_preset_name
from .reports import markdown_report
from .scanners import parse_modules, scan_dns, scan_extra_modules, scan_nmap, scan_whois
from .target import normalize_target, resolve_target, reverse_lookup, target_has_scan_endpoint

DB_PATH = Path(__file__).resolve().parent.parent / "reconkit_web.db"

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReconKit Web Panel</title>
<style>
:root{--bg:#08111f;--card:#101a31;--line:#26385f;--text:#dbeafe;--muted:#93a4bd;--cyan:#67e8f9;--pink:#e879f9;--green:#34d399;--red:#fb7185;--yellow:#fbbf24;--btn:#6d28d9;--btn2:#1f2a44}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top left,#172554 0,#08111f 38%,#050816 100%);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif}a{color:var(--cyan)}.wrap{max-width:1280px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:18px}.brand{font-size:28px;font-weight:900;color:var(--pink)}.sub{color:var(--muted);font-size:13px}.tabs{display:flex;gap:8px;flex-wrap:wrap}.tab{border:1px solid var(--line);background:#0f172a;color:var(--text);padding:9px 12px;border-radius:10px;cursor:pointer}.tab.active{border-color:var(--pink);color:#fff;background:#3b0764}.grid{display:grid;grid-template-columns:360px 1fr;gap:18px}.card{background:linear-gradient(180deg,rgba(16,26,49,.96),rgba(10,17,32,.96));border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 20px 80px rgba(0,0,0,.25)}h2{margin:0 0 14px;color:var(--cyan)}label{display:block;font-size:12px;color:var(--muted);margin:10px 0 5px}input,select,textarea{width:100%;border:1px solid var(--line);background:#080f20;color:var(--text);border-radius:10px;padding:9px}textarea{min-height:120px;font-family:ui-monospace,monospace}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.checks{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.checks label{display:flex;align-items:center;gap:6px;margin:0;font-size:13px}.checks input{width:auto}.btn{border:0;background:var(--btn);color:white;border-radius:10px;padding:10px 14px;cursor:pointer;font-weight:700}.btn.secondary{background:var(--btn2);border:1px solid var(--line)}.btn.danger{background:#991b1b}.btn:disabled{opacity:.6;cursor:not-allowed}.hidden{display:none}.badge{display:inline-block;padding:3px 8px;border-radius:999px;font-size:12px;border:1px solid var(--line)}.ok{background:#052e2b;color:var(--green)}.warn{background:#422006;color:var(--yellow)}.err{background:#450a0a;color:var(--red)}.run{background:#172554;color:#93c5fd}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--cyan)}pre{white-space:pre-wrap;overflow:auto;background:#070d1b;border:1px solid var(--line);border-radius:12px;padding:12px;max-height:420px}.panel{display:none}.panel.active{display:block}.actions{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.note{color:var(--muted);font-size:13px}.mono{font-family:ui-monospace,Menlo,Consolas,monospace}.full{grid-column:1/-1}.statusbar{margin:0 0 14px;padding:12px;border:1px solid var(--line);border-radius:14px;background:#0b1326}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0}.metric{background:#081127;border:1px solid var(--line);border-radius:14px;padding:12px}.metric b{display:block;color:var(--cyan);font-size:20px}.progress{height:8px;background:#111c35;border-radius:999px;overflow:hidden;margin:10px 0}.progress i{display:block;height:100%;width:45%;background:linear-gradient(90deg,var(--cyan),var(--pink));animation:pulse 1.2s infinite alternate}@keyframes pulse{from{opacity:.55;transform:translateX(-35%)}to{opacity:1;transform:translateX(140%)}}.sectionTitle{color:var(--pink);font-weight:800;margin-top:18px}.full{grid-column:1/-1}@media(max-width:900px){.grid{grid-template-columns:1fr}.top{display:block}.tabs{margin-top:14px}}
</style>
</head>
<body><div class="wrap">
<header class="top"><div><div class="brand">⚡ ReconKit Web Panel</div><div class="sub">Local dashboard by Team CynetX • v__VERSION__ • __WEBSITE__</div></div><nav class="tabs"><button class="tab active" onclick="tab('scan',event)">Scan</button><button class="tab" onclick="tab('history',event)">History</button><button class="tab" onclick="tab('presets',event)">Presets</button><button class="tab" onclick="tab('deps',event)">Dependencies</button><button class="tab" onclick="tab('ai',event)">AI Config</button><button class="tab" onclick="tab('about',event)">About</button></nav></header>
<section id="scan" class="panel active"><div id="activeBox" class="statusbar note">Checking scanner status...</div><div class="grid"><div class="card"><h2>New Scan</h2><form onsubmit="startScan(event)"><label>Target</label><input id="target" required placeholder="example.com or 127.0.0.1"><div class="row"><div><label>Mode</label><select id="mode"><option>fast</option><option selected>balanced</option><option>deep</option></select></div><div><label>Preset</label><select id="preset"><option>standard</option><option>quick</option><option>full</option><option>web</option><option>vuln</option></select></div></div><label>Modules</label><input id="modules" value="safe" placeholder="safe, web,tls, mission"><label>Ports</label><input id="ports" placeholder="80,443,8080"><div class="row"><div><label>Timeout</label><input id="timeout" type="number" min="10" value="90"></div><div><label>Raw Dir</label><input id="rawdir" placeholder="artifacts"></div></div><div class="checks"><label><input id="aggressive" type="checkbox">Aggressive</label><label><input id="nowhois" type="checkbox">No WHOIS</label><label><input id="ai" type="checkbox">AI</label><label><input id="cmd" type="checkbox">Show commands</label></div><button id="runBtn" class="btn" type="submit">Run Scan</button></form><p class="note">Panel is local-first. Bind to 127.0.0.1 unless you intentionally expose it on a trusted server.</p></div><div class="card"><h2>Result Viewer</h2><div id="result" class="note">Run a scan or open one from History.</div></div></div></section>
<section id="history" class="panel"><div class="card"><div class="actions"><button class="btn secondary" onclick="loadHistory()">Refresh</button></div><div id="historyBox"></div></div></section>
<section id="presets" class="panel"><div class="grid"><div class="card"><h2>Create Preset</h2><form onsubmit="savePreset(event)"><label>Name</label><input id="pname" required placeholder="myweb"><div class="row"><div><label>Base</label><select id="pbase"><option>standard</option><option>quick</option><option>full</option><option>web</option><option>vuln</option></select></div><div><label>Strategy</label><select id="pstrategy"><option selected>append</option><option>replace</option><option>only</option></select></div></div><label>Description</label><input id="pdesc" placeholder="Short note for this preset"><p class="note">Fill only the tools you want to customize. Empty fields are skipped automatically.</p><label>Nmap args</label><input id="pt_nmap" placeholder="-sV -sC -Pn -p 80,443 -oN - {target}"><label>WhatWeb args</label><input id="pt_whatweb" placeholder="--color=never {url}"><label>HTTPX args</label><input id="pt_httpx" placeholder="-silent -title -status-code -u {url}"><label>WAFW00F args</label><input id="pt_wafw00f" placeholder="-a {url}"><label>Nikto args</label><input id="pt_nikto" placeholder="-host {url}"><label>Nuclei args</label><input id="pt_nuclei" placeholder="-silent -u {url}"><details><summary class="note">Advanced: more tools as JSON</summary><textarea id="pargs" placeholder='{"dig":"A {target}","sslscan":"{target}","katana":"-u {url}"}'></textarea></details><button class="btn" type="submit">Save Preset</button></form></div><div class="card"><h2>Saved Presets</h2><div class="actions"><button class="btn secondary" onclick="loadPresets()">Refresh</button></div><div id="presetBox"></div></div></div></section>
<section id="deps" class="panel"><div class="card"><h2>Dependencies</h2><div class="actions"><button class="btn secondary" onclick="loadDeps()">Refresh</button><button class="btn secondary" onclick="installDeps(true)">Install Required + Optional</button><button class="btn secondary" onclick="installDeps(false)">Install Required Only</button></div><div id="depsBox"></div></div></section>
<section id="ai" class="panel"><div class="grid"><div class="card"><h2>AI Settings</h2><form onsubmit="saveAI(event)"><label>Provider</label><input id="ai_provider" placeholder="openrouter"><label>Endpoint URL</label><input id="ai_endpoint" placeholder="https://openrouter.ai/api/v1/chat/completions"><label>Model</label><input id="ai_model" placeholder="openrouter/free"><label>API Key Environment Variable</label><input id="ai_env" placeholder="OPENROUTER_API_KEY"><label>Direct API Key (local config only)</label><input id="ai_key" placeholder="leave empty to keep current direct key"><div class="row"><div><label>Temperature</label><input id="ai_temp" type="number" step="0.01"></div><div><label>Max Tokens</label><input id="ai_tokens" type="number"></div></div><div class="row"><div><label>Continuation Rounds</label><input id="ai_rounds" type="number"></div><div><label>Empty Response Retries</label><input id="ai_retries" type="number"></div></div><div class="row"><div><label>HTTP Referer</label><input id="ai_ref"></div><div><label>X-Title</label><input id="ai_title"></div></div><label>System Prompt</label><textarea id="ai_prompt"></textarea><button class="btn" type="submit">Save AI Config</button> <button type="button" class="btn secondary" onclick="testAI()">Test AI</button><p class="note">Default provider is OpenRouter. Direct keys are stored only in local recon_config.json; env vars are safer for shared servers.</p></form></div><div class="card"><h2>Current AI Config</h2><pre id="aiBox">Loading...</pre></div></div></section>
<section id="about" class="panel"><div class="card"><h2>About ReconKit</h2><p>ReconKit combines real CLI tools and normalized reporting into a local dashboard. Use it only on assets you own or have permission to test.</p><ul><li>Website: <a href="__WEBSITE__">__WEBSITE__</a></li><li>Telegram: <a href="__TELEGRAM__">__TELEGRAM__</a></li></ul><pre>CLI examples:
reconkit example.com --mission -o scan.json --html report.html
reconkit --preset-create
reconkit --ai-show
reconkit --check-deps</pre></div></section>
</div><script>
const $=id=>document.getElementById(id);let activePoll=null;function tab(id,ev){document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));$(id).classList.add('active');if(ev&&ev.target)ev.target.classList.add('active');if(id==='history')loadHistory();if(id==='presets')loadPresets();if(id==='deps')loadDeps();if(id==='ai')loadAI();}
async function api(path,opts={}){opts.headers=Object.assign({'Content-Type':'application/json'},opts.headers||{});const r=await fetch(path,opts);const t=await r.text();let j=null;try{j=t?JSON.parse(t):null}catch(e){}if(!r.ok)throw new Error((j&&j.error)||t||r.status);return j;}
function statusBadge(s){let c=s==='completed'||s==='found'?'ok':s==='failed'||s==='missing'?'err':s==='running'||s==='queued'?'run':'warn';return `<span class="badge ${c}">${s}</span>`}
async function refreshStatus(){try{let d=await api('/api/status');let a=d.active_scan;if(a){$('activeBox').innerHTML=`${statusBadge(a.status)} Active scan: <b>${esc(a.target)}</b> <span class="mono">${esc(a.scan_id)}</span><div class="progress"><i></i></div><span class="note">${esc(a.progress||'Working...')}</span>`;$('runBtn').disabled=true;$('runBtn').textContent='Scan running...';if(!activePoll){activePoll=setInterval(refreshStatus,1800)}}else{$('activeBox').innerHTML='No active scan. Ready to run a new job.';$('runBtn').disabled=false;$('runBtn').textContent='Run Scan';if(activePoll){clearInterval(activePoll);activePoll=null}}}catch(e){$('activeBox').textContent='Status check failed: '+e.message}}
async function startScan(e){e.preventDefault();const body={target:$('target').value.trim(),mode:$('mode').value,preset:$('preset').value,modules:$('modules').value||'safe',ports:$('ports').value||null,timeout:Number($('timeout').value||90),raw_dir:$('rawdir').value||null,aggressive:$('aggressive').checked,no_whois:$('nowhois').checked,ai:$('ai').checked,show_commands:$('cmd').checked};try{const d=await api('/api/scan',{method:'POST',body:JSON.stringify(body)});$('result').innerHTML=`${statusBadge('queued')} <span class="mono">${d.scan_id}</span>`;poll(d.scan_id);refreshStatus();}catch(err){alert(err.message)}}
function poll(id){let timer=setInterval(async()=>{try{let d=await api('/api/scan/'+id);$('result').innerHTML=renderScan(d);if(['completed','failed'].includes(d.status))clearInterval(timer);}catch(e){clearInterval(timer);alert(e.message)}},1800)}
function esc(v){return String(v??'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}
function renderScan(d){let r=d.report||{};let ports=(r.nmap_ports||[]).filter(p=>p.state==='open');let extras=r.extras||[];let notes=r.notes||[];let h=`<div class="actions"><a class="btn secondary" href="/api/scan/${d.scan_id}/report/json" target="_blank">JSON</a><a class="btn secondary" href="/api/scan/${d.scan_id}/report/markdown" target="_blank">Markdown</a><a class="btn secondary" href="/api/scan/${d.scan_id}/report/html" target="_blank">HTML</a>${d.status==='completed'?`<button class="btn secondary" onclick="runAI('${d.scan_id}')">Run AI</button>`:''}</div>`;h+=`<p>${statusBadge(d.status)} <b>${esc(d.progress||'')}</b></p>`;if(d.status==='running'||d.status==='queued')h+=`<div class="progress"><i></i></div>`;h+=`<div class="metrics"><div class="metric"><span>Target</span><b>${esc(d.target)}</b></div><div class="metric"><span>Open Ports</span><b>${ports.length}</b></div><div class="metric"><span>Resolved IPs</span><b>${(r.resolved_ips||[]).length}</b></div><div class="metric"><span>Elapsed</span><b>${d.elapsed||0}s</b></div></div>`;h+=`<p class="note">Mode: ${esc(d.mode)} • Preset: ${esc(d.preset)} • Scan ID: <span class="mono">${esc(d.scan_id)}</span></p>`;if(d.error)h+=`<pre>${esc(d.error)}</pre>`;h+=`<div class="sectionTitle">Resolved IPs</div><pre>${esc((r.resolved_ips||[]).join('\n')||'none')}</pre>`;h+=`<div class="sectionTitle">Open Ports & Services</div>`;if(ports.length){h+='<table><tr><th>Port</th><th>State</th><th>Service</th><th>Version</th></tr>';ports.forEach(p=>h+=`<tr><td class="mono">${esc(p.port)}</td><td>${esc(p.state)}</td><td>${esc(p.service)}</td><td>${esc(p.version||'')}</td></tr>`);h+='</table>'}else h+='<p class="note">No open ports recorded yet.</p>';h+=`<div class="sectionTitle">DNS Records</div><pre>${esc(JSON.stringify(r.dns_records||{},null,2))}</pre>`;h+=`<div class="sectionTitle">Extra Tooling</div>`;if(extras.length){h+='<table><tr><th>Module</th><th>Tool</th><th>Status</th><th>Summary</th></tr>';extras.forEach(e=>h+=`<tr><td>${esc(e.module)}</td><td>${esc(e.tool)}</td><td>${statusBadge(e.missing?'missing':(e.ok?'ok':'warn'))}</td><td>${esc((e.summary||[]).join(' | '))}</td></tr>`);h+='</table>'}else h+='<p class="note">No extra tool output yet.</p>';h+=`<div class="sectionTitle">Notes</div><pre>${esc(notes.join('\n')||'none')}</pre>`;if(d.ai_output)h+=`<div class="sectionTitle">AI Analysis</div><pre>${esc(d.ai_output)}</pre>`;return h;}
async function loadHistory(){let d=await api('/api/scans');let h='<table><tr><th>ID</th><th>Target</th><th>Mode</th><th>Preset</th><th>Status</th><th>Started</th><th>Actions</th></tr>';(d.scans||[]).forEach(s=>h+=`<tr><td class="mono">${s.scan_id}</td><td>${s.target}</td><td>${s.mode}</td><td>${s.preset}</td><td>${statusBadge(s.status)}</td><td>${s.started_at||''}</td><td><button class="btn secondary" onclick="openScan('${s.scan_id}')">Open</button> <button class="btn danger" onclick="deleteScan('${s.scan_id}')">Delete</button></td></tr>`);$('historyBox').innerHTML=h+'</table>'}
async function openScan(id){tab('scan');let d=await api('/api/scan/'+id);$('result').innerHTML=renderScan(d)}async function deleteScan(id){if(confirm('Delete scan?')){await api('/api/scan/'+id,{method:'DELETE'});loadHistory()}}
async function runAI(id){$('result').innerHTML+='<p>Running AI...</p>';let d=await api('/api/scan/'+id+'/ai',{method:'POST',body:'{}'});openScan(id)}
async function loadPresets(){let d=await api('/api/presets');let h='<table><tr><th>Name</th><th>Type</th><th>Base</th><th>Mode</th><th>Description</th><th>Action</th></tr>';(d.presets||[]).forEach(p=>h+=`<tr><td>${p.name}</td><td>${p.type}</td><td>${p.base}</td><td>${p.strategy}</td><td>${p.description||''}</td><td>${p.type==='custom'?`<button class="btn danger" onclick="deletePreset('${p.name}')">Delete</button>`:''}</td></tr>`);$('presetBox').innerHTML=h+'</table>';let sel=$('preset');let current=sel.value;sel.innerHTML=(d.presets||[]).map(p=>`<option>${p.name}</option>`).join('');sel.value=current||'standard'}
async function savePreset(e){e.preventDefault();let args={};let toolFields={nmap:'pt_nmap',whatweb:'pt_whatweb',httpx:'pt_httpx',wafw00f:'pt_wafw00f',nikto:'pt_nikto',nuclei:'pt_nuclei'};Object.entries(toolFields).forEach(([tool,id])=>{let v=$(id).value.trim();if(v)args[tool]=v});try{let extra=$('pargs').value.trim()?JSON.parse($('pargs').value):{};args=Object.assign(args,extra)}catch(err){alert('Advanced JSON must be valid JSON');return}if(!Object.keys(args).length){alert('Add args for at least one tool. Example: nmap = -sV -Pn -p 80,443 {target}');return}let body={name:$('pname').value,base:$('pbase').value,strategy:$('pstrategy').value,description:$('pdesc').value,tool_args:args};try{await api('/api/presets',{method:'POST',body:JSON.stringify(body)});['pname','pdesc','pt_nmap','pt_whatweb','pt_httpx','pt_wafw00f','pt_nikto','pt_nuclei','pargs'].forEach(id=>$(id).value='');loadPresets();alert('Preset saved')}catch(err){alert(err.message)}}async function deletePreset(n){if(confirm('Delete preset '+n+'?')){await api('/api/presets/'+encodeURIComponent(n),{method:'DELETE'});loadPresets()}}
async function loadDeps(){let d=await api('/api/deps');let h='<table><tr><th>Tool</th><th>Type</th><th>Status</th></tr>';(d.deps||[]).forEach(x=>h+=`<tr><td>${x.tool}</td><td>${x.kind}</td><td>${statusBadge(x.status)}</td></tr>`);$('depsBox').innerHTML=h+'</table>'}async function installDeps(opt){if(confirm('Install dependencies on this system?'))await api('/api/deps/install',{method:'POST',body:JSON.stringify({include_optional:opt})})}
async function loadAI(){let d=await api('/api/ai/config');$('aiBox').textContent=JSON.stringify(d.config,null,2);$('ai_provider').value=d.config.provider||'openrouter';$('ai_endpoint').value=d.config.endpoint_url||'https://openrouter.ai/api/v1/chat/completions';$('ai_model').value=d.config.model||'openrouter/free';$('ai_env').value=d.config.api_key_env||'OPENROUTER_API_KEY';$('ai_temp').value=d.config.temperature||0.2;$('ai_tokens').value=d.config.max_tokens||3200;$('ai_rounds').value=d.config.continuation_rounds||3;$('ai_retries').value=d.config.empty_response_retries||3;$('ai_ref').value=d.config.http_referer||'https://local.reconkit';$('ai_title').value=d.config.x_title||'ReconKit AI Analysis';$('ai_prompt').value=d.config.system_prompt||'';$('ai_key').value=''}
async function saveAI(e){e.preventDefault();let cfg={provider:$('ai_provider').value,endpoint_url:$('ai_endpoint').value,model:$('ai_model').value,api_key_env:$('ai_env').value,temperature:$('ai_temp').value,max_tokens:$('ai_tokens').value,continuation_rounds:$('ai_rounds').value,empty_response_retries:$('ai_retries').value,http_referer:$('ai_ref').value,x_title:$('ai_title').value,system_prompt:$('ai_prompt').value};if($('ai_key').value)cfg.api_key=$('ai_key').value;try{await api('/api/ai/config',{method:'POST',body:JSON.stringify(cfg)});loadAI();alert('AI config saved')}catch(err){alert(err.message)}}async function testAI(){try{let d=await api('/api/ai/test',{method:'POST',body:'{}'});alert('AI OK: '+d.reply)}catch(err){alert(err.message)}}
loadPresets();refreshStatus();setInterval(refreshStatus,5000);
</script></body></html>'''


def ensure_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            scan_id TEXT PRIMARY KEY, target TEXT NOT NULL, mode TEXT, modules TEXT, preset TEXT,
            ports TEXT, timeout INTEGER, aggressive INTEGER, no_whois INTEGER, ai INTEGER,
            show_commands INTEGER, raw_dir TEXT, status TEXT, started_at TEXT, finished_at TEXT,
            elapsed REAL, progress TEXT, report_json TEXT, ai_output TEXT, error TEXT
        )
    """)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(scans)").fetchall()}
    if "progress" not in columns:
        conn.execute("ALTER TABLE scans ADD COLUMN progress TEXT")
    conn.commit()
    return conn

_CONN: sqlite3.Connection | None = None
_LOCK = threading.Lock()
_SCAN_LOCK = threading.Lock()


def conn() -> sqlite3.Connection:
    global _CONN
    with _LOCK:
        if _CONN is None:
            _CONN = ensure_db()
        return _CONN


def active_scan() -> dict[str, Any] | None:
    row = conn().execute("SELECT scan_id,target,mode,preset,status,started_at,progress FROM scans WHERE status IN ('queued','running') ORDER BY started_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def insert_scan(params: dict[str, Any]) -> str:
    scan_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn().execute("""
        INSERT INTO scans (scan_id,target,mode,modules,preset,ports,timeout,aggressive,no_whois,ai,show_commands,raw_dir,status,started_at,elapsed,progress)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)
    """, (scan_id, params["target"], params.get("mode", "fast"), params.get("modules", "safe"), params.get("preset", "standard"), params.get("ports"), int(params.get("timeout") or 90), int(bool(params.get("aggressive"))), int(bool(params.get("no_whois"))), int(bool(params.get("ai"))), int(bool(params.get("show_commands"))), params.get("raw_dir"), "queued", now, "Queued and waiting to start"))
    conn().commit()
    return scan_id


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    for key in ("aggressive", "no_whois", "ai", "show_commands"):
        data[key] = bool(data.get(key))
    if data.get("report_json"):
        data["report"] = json.loads(data["report_json"])
    else:
        data["report"] = None
    data.pop("report_json", None)
    return data


def get_scan(scan_id: str) -> dict[str, Any] | None:
    return row_to_dict(conn().execute("SELECT * FROM scans WHERE scan_id=?", (scan_id,)).fetchone())


def update_scan(scan_id: str, **fields: Any) -> None:
    if not fields:
        return
    if fields.get("status") in {"completed", "failed"}:
        fields.setdefault("finished_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    keys = list(fields)
    vals = [fields[k] for k in keys] + [scan_id]
    conn().execute(f"UPDATE scans SET {', '.join(k + '=?' for k in keys)} WHERE scan_id=?", vals)
    conn().commit()


def list_scans() -> list[dict[str, Any]]:
    rows = conn().execute("SELECT scan_id,target,mode,preset,status,started_at,elapsed,progress FROM scans ORDER BY started_at DESC").fetchall()
    return [dict(r) for r in rows]


def reset_stale_scans() -> None:
    conn().execute(
        "UPDATE scans SET status='failed', progress='Interrupted because the web panel restarted', error='Web panel restarted before the scan finished', finished_at=? WHERE status IN ('queued','running')",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"),),
    )
    conn().commit()


def report_from_dict(data: dict[str, Any]) -> ReconReport:
    report = ReconReport(target=data.get("target", ""), normalized_target=data.get("normalized_target", data.get("target", "")), started_at=data.get("started_at", ""), profile=data.get("profile", "fast"))
    for key, value in data.items():
        if not hasattr(report, key):
            continue
        if key == "extras":
            extras: list[ExtraResult] = []
            for item in value or []:
                if isinstance(item, ExtraResult):
                    extras.append(item)
                elif isinstance(item, dict):
                    extras.append(ExtraResult(
                        module=str(item.get("module", "")),
                        tool=str(item.get("tool", "")),
                        ok=bool(item.get("ok")),
                        summary=[str(line) for line in item.get("summary", [])],
                        missing=bool(item.get("missing")),
                        elapsed=float(item.get("elapsed", 0) or 0),
                    ))
            setattr(report, key, extras)
        elif key == "findings":
            findings: list[Finding] = []
            for item in value or []:
                if isinstance(item, Finding):
                    findings.append(item)
                elif isinstance(item, dict):
                    findings.append(Finding(
                        title=str(item.get("title", "")),
                        severity=str(item.get("severity", "")),
                        evidence=str(item.get("evidence", "")),
                        recommendation=str(item.get("recommendation", "")),
                        confidence=str(item.get("confidence", "medium")),
                    ))
            setattr(report, key, findings)
        else:
            setattr(report, key, value)
    return report


def report_to_dict(report: ReconReport) -> dict[str, Any]:
    data = report.__dict__.copy()
    data["extras"] = [item.__dict__ for item in report.extras]
    data["findings"] = [item.__dict__ for item in report.findings]
    data["generated_by"] = {"name": APP, "author": AUTHOR, "website": WEBSITE, "telegram": TELEGRAM}
    return data


def set_progress(scan_id: str, message: str, started: float | None = None) -> None:
    fields: dict[str, Any] = {"progress": message}
    if started is not None:
        fields["elapsed"] = round(time.monotonic() - started, 2)
    update_scan(scan_id, **fields)


def run_scan_worker(scan_id: str) -> None:
    started = time.monotonic()
    acquired = _SCAN_LOCK.acquire(blocking=False)
    if not acquired:
        update_scan(scan_id, status="failed", progress="Another scan is already running", error="Another scan is already running")
        return
    scan = get_scan(scan_id)
    if not scan:
        _SCAN_LOCK.release()
        return
    try:
        update_scan(scan_id, status="running", progress="Normalizing target and validating preset")
        target = normalize_target(scan["target"])
        if not preset_exists(scan.get("preset") or "standard"):
            raise ValueError(f"Unknown scan preset: {scan.get('preset')}")
        modules = parse_modules(scan.get("modules") or "safe")
        set_progress(scan_id, "Resolving DNS and reverse DNS", started)
        report = ReconReport(target=scan["target"], normalized_target=target, started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), profile=scan.get("mode") or "fast")
        report.resolved_ips = resolve_target(target)
        if not report.resolved_ips:
            report.notes.append("No IPs resolved through system resolver.")
        for ip in report.resolved_ips:
            report.reverse_dns[ip] = reverse_lookup(ip)
        timeout = max(10, int(scan.get("timeout") or 90))
        set_progress(scan_id, "Collecting DNS records", started)
        preset = scan.get("preset") or "standard"
        if preset_strategy(preset) == "only" and not preset_tool_args(preset, "dig"):
            report.notes.append("Default DNS record scan skipped because scan preset mode is only.")
        else:
            scan_dns(target, timeout, report)
        set_progress(scan_id, "Running nmap scan", started)
        if target_has_scan_endpoint(report):
            scan_nmap(target, timeout, report, scan.get("ports"), (scan.get("mode") == "deep"), preset)
        else:
            report.notes.append("Skipping nmap: target did not resolve to an IP.")
        set_progress(scan_id, "Running selected extra modules", started)
        if modules:
            raw_dir = Path(scan["raw_dir"]) if scan.get("raw_dir") else None
            scan_extra_modules(report, timeout, modules, bool(scan.get("aggressive")), raw_dir, preset)
        set_progress(scan_id, "Collecting WHOIS summary", started)
        if not scan.get("no_whois"):
            scan_whois(target, timeout, report, preset)
        set_progress(scan_id, "Finalizing report", started)
        report.elapsed_seconds = time.monotonic() - started
        report_json = json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)
        update_scan(scan_id, elapsed=round(report.elapsed_seconds, 2), report_json=report_json)
        if scan.get("ai"):
            set_progress(scan_id, "Running AI analysis", started)
            try:
                run_ai_for_scan(scan_id, report)
                set_progress(scan_id, "AI analysis completed", started)
            except Exception as ai_exc:
                report.notes.append(f"AI analysis failed: {ai_exc}")
                report_json = json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)
                update_scan(scan_id, report_json=report_json, error=f"AI analysis failed: {ai_exc}")
        update_scan(scan_id, status="completed", elapsed=round(report.elapsed_seconds, 2), progress="Scan completed", report_json=report_json)
    except Exception as exc:
        update_scan(scan_id, status="failed", elapsed=round(time.monotonic() - started, 2), progress="Scan failed", error=str(exc))
    finally:
        _SCAN_LOCK.release()


def run_ai_for_scan(scan_id: str, report: ReconReport | None = None) -> str:
    scan = get_scan(scan_id)
    if not scan:
        raise ValueError("scan not found")
    if report is None:
        if not scan.get("report"):
            raise ValueError("scan report not found")
        report = report_from_dict(scan["report"])
    cfg = load_config()
    validate_ai_config(cfg)
    key = ai_api_key(cfg)
    if not key:
        raise ValueError(ai_key_hint(cfg))
    text = call_openrouter(report, cfg, key, int(scan.get("timeout") or 90), colorize=False)
    update_scan(scan_id, ai_output=text)
    return text


def html_report_from_markdown(md: str) -> str:
    import html
    body = []
    for line in md.splitlines():
        escaped = html.escape(line)
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body.append(f"<p>• {html.escape(line[2:])}</p>")
        elif line.strip():
            body.append(f"<p>{escaped}</p>")
    return "<!doctype html><html><head><meta charset='utf-8'><title>ReconKit Report</title><style>body{font-family:Segoe UI,Arial;background:#08111f;color:#dbeafe;max-width:1050px;margin:30px auto;line-height:1.5}h1,h2{color:#67e8f9}p{background:#101a31;border:1px solid #26385f;border-radius:10px;padding:10px}</style></head><body>" + "\n".join(body) + "</body></html>"


class Handler(BaseHTTPRequestHandler):
    server_version = "ReconKitWeb/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_data(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(raw)

    def send_text(self, text: str, content_type: str = "text/plain; charset=utf-8", status: int = 200, filename: str | None = None) -> None:
        raw = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(raw)

    def error_json(self, message: str, status: int = 400) -> None:
        self.send_data({"error": message}, status)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/":
                page = HTML.replace("__VERSION__", VERSION).replace("__WEBSITE__", WEBSITE).replace("__TELEGRAM__", TELEGRAM)
                return self.send_text(page, "text/html; charset=utf-8")
            if path == "/api/status":
                return self.send_data({"app": APP, "version": VERSION, "author": AUTHOR, "website": WEBSITE, "web_panel": "live-progress-ai-preset-v2", "active_scan": active_scan()})
            if path == "/api/scans":
                return self.send_data({"scans": list_scans()})
            if path.startswith("/api/scan/"):
                parts = path.strip("/").split("/")
                scan_id = parts[2]
                scan = get_scan(scan_id)
                if not scan:
                    return self.error_json("scan not found", 404)
                if len(parts) == 3:
                    return self.send_data(scan)
                if len(parts) == 5 and parts[3] == "report":
                    report = scan.get("report")
                    if not report:
                        return self.error_json("report not found", 404)
                    fmt = parts[4]
                    if fmt == "json":
                        return self.send_text(json.dumps(report, ensure_ascii=False, indent=2), "application/json; charset=utf-8", filename=f"{scan_id}.json")
                    md = markdown_report(report_from_dict(report))
                    if fmt == "markdown":
                        return self.send_text(md, "text/markdown; charset=utf-8", filename=f"{scan_id}.md")
                    if fmt == "html":
                        return self.send_text(html_report_from_markdown(md), "text/html; charset=utf-8", filename=f"{scan_id}.html")
                    return self.error_json("unknown report format", 400)
            if path == "/api/presets":
                return self.send_data({"presets": [{"name": r[0], "type": r[1], "base": r[2], "strategy": r[3], "description": r[4]} for r in list_preset_rows()]})
            if path == "/api/deps":
                return self.send_data({"deps": [{"tool": r[0], "kind": r[1], "status": r[2]} for r in dependency_rows()]})
            if path == "/api/ai/config":
                return self.send_data({"config": safe_config_for_display(load_config())})
            return self.error_json("not found", 404)
        except Exception as exc:
            return self.error_json(str(exc), 500)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        try:
            body = self.read_json()
            if path == "/api/scan":
                current = active_scan()
                if current:
                    return self.error_json(f"Another scan is already running: {current.get('scan_id')} ({current.get('target')})", 409)
                target = str(body.get("target", "")).strip()
                if not target:
                    return self.error_json("target is required", 400)
                body["target"] = target
                scan_id = insert_scan(body)
                threading.Thread(target=run_scan_worker, args=(scan_id,), daemon=True).start()
                return self.send_data({"scan_id": scan_id, "status": "queued"})
            if path.endswith("/ai") and path.startswith("/api/scan/"):
                scan_id = path.strip("/").split("/")[2]
                text = run_ai_for_scan(scan_id)
                return self.send_data({"scan_id": scan_id, "ai_output": text})
            if path == "/api/presets":
                name = validate_preset_name(str(body.get("name", "")))
                tool_args = body.get("tool_args") or {}
                if not isinstance(tool_args, dict):
                    return self.error_json("tool_args must be an object", 400)
                create_preset(name, str(body.get("base", "standard")), tool_args, str(body.get("description", "")), str(body.get("strategy", "append")))
                return self.send_data({"ok": True, "name": name})
            if path == "/api/deps/install":
                include_optional = bool(body.get("include_optional", True))
                threading.Thread(target=install_deps, args=(include_optional, False), kwargs={"colorize": False}, daemon=True).start()
                return self.send_data({"started": True})
            if path == "/api/ai/config":
                assignments = [f"{k}={v}" for k, v in body.items() if v is not None]
                cfg = apply_ai_config_updates(load_config(), assignments, [])
                validate_ai_config(cfg)
                save_config(cfg)
                return self.send_data({"ok": True, "config": safe_config_for_display(cfg)})
            if path == "/api/ai/test":
                cfg = load_config()
                validate_ai_config(cfg)
                key = ai_api_key(cfg)
                if not key:
                    return self.error_json(ai_key_hint(cfg), 400)
                reply = test_ai_connection(cfg, key, 60)
                return self.send_data({"ok": True, "reply": reply})
            return self.error_json("not found", 404)
        except Exception as exc:
            return self.error_json(str(exc), 500)

    def do_DELETE(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        try:
            if path.startswith("/api/scan/"):
                scan_id = path.strip("/").split("/")[2]
                cur = conn().execute("DELETE FROM scans WHERE scan_id=?", (scan_id,))
                conn().commit()
                return self.send_data({"deleted": cur.rowcount > 0})
            if path.startswith("/api/presets/"):
                name = urllib.parse.unquote(path.strip("/").split("/", 2)[2])
                return self.send_data({"deleted": delete_preset(name)})
            return self.error_json("not found", 404)
        except Exception as exc:
            return self.error_json(str(exc), 500)


def run_web_panel(host: str = "127.0.0.1", port: int = 8080) -> int:
    ensure_db()
    reset_stale_scans()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[◆] Starting {APP} Web Panel: http://{host}:{port}")
    print("[!] Keep it on 127.0.0.1 unless you are on a trusted server/network.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Web panel stopped")
    finally:
        server.server_close()
    return 0
