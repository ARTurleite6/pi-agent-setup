#!/usr/bin/env python3
"""Render a self-contained interactive HTML Pi usage-audit report."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import stat
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRIORITIES = {"high", "medium", "low"}


class SpecError(ValueError):
    pass


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def require(mapping: dict[str, Any], key: str, expected: type) -> Any:
    value = mapping.get(key)
    if not isinstance(value, expected):
        raise SpecError(f"{key!r} must be {expected.__name__}")
    return value


def validate(spec: dict[str, Any]) -> None:
    report = require(spec, "report", dict)
    report_id = require(report, "id", str)
    if not ID_PATTERN.fullmatch(report_id):
        raise SpecError("report.id must contain lowercase letters, numbers, and single hyphens")
    period = require(report, "period", dict)
    require(period, "start", str)
    require(period, "end", str)
    require(period, "selection", str)
    require(spec, "executive_summary", str)
    require(spec, "metrics", list)
    require(spec, "sections", list)
    actions = require(spec, "actions", list)
    seen: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            raise SpecError("every action must be an object")
        action_id = require(action, "id", str)
        if not ID_PATTERN.fullmatch(action_id) or action_id in seen:
            raise SpecError(f"invalid or duplicate action id: {action_id}")
        seen.add(action_id)
        if action.get("priority") not in PRIORITIES:
            raise SpecError(f"invalid priority for action {action_id}")
        for key in ("theme", "title", "status", "kind", "recommendation", "rationale"):
            require(action, key, str)
        require(action, "evidence", list)
        require(action, "implementation", list)


def observation_card(observation: dict[str, Any]) -> str:
    return f"""
      <article class="observation">
        <h3>{esc(observation.get('title', 'Observation'))}</h3>
        <p>{esc(observation.get('interpretation', ''))}</p>
        <div class="evidence"><span>Evidence</span>{esc(observation.get('evidence', ''))}</div>
      </article>"""


def action_card(action: dict[str, Any]) -> str:
    evidence = "".join(f"<li>{esc(item)}</li>" for item in action.get("evidence", []))
    implementation = "".join(f"<li>{esc(item)}</li>" for item in action.get("implementation", []))
    checked = " checked" if action.get("selected_by_default") else ""
    return f"""
      <article class="action-card" data-status="{esc(action['status'])}" data-priority="{esc(action['priority'])}">
        <label class="action-select">
          <input type="checkbox" class="action-checkbox" value="{esc(action['id'])}"{checked}>
          <span class="checkmark" aria-hidden="true"></span>
          <span class="sr-only">Select {esc(action['title'])}</span>
        </label>
        <div class="action-main">
          <div class="badges">
            <span class="badge priority-{esc(action['priority'])}">{esc(action['priority'])}</span>
            <span class="badge status">{esc(action['status'])}</span>
            <span class="badge kind">{esc(action['kind'])}</span>
          </div>
          <h3>{esc(action['title'])}</h3>
          <p class="recommendation">{esc(action['recommendation'])}</p>
          <p>{esc(action['rationale'])}</p>
          <details>
            <summary>Evidence and implementation</summary>
            <h4>Evidence</h4><ul>{evidence}</ul>
            <h4>Implementation</h4><ol>{implementation}</ol>
          </details>
        </div>
      </article>"""


def render(spec: dict[str, Any]) -> str:
    validate(spec)
    report = spec["report"]
    period = report["period"]
    metrics = "".join(
        f"<article class='metric'><strong>{esc(item.get('value', ''))}</strong><span>{esc(item.get('label', ''))}</span><small>{esc(item.get('detail', ''))}</small></article>"
        for item in spec["metrics"]
    )

    section_html = []
    nav_html = ["<a href='#overview'>Overview</a>"]
    for section in spec["sections"]:
        section_id = section.get("id", "section")
        if not ID_PATTERN.fullmatch(str(section_id)):
            raise SpecError(f"invalid section id: {section_id}")
        nav_html.append(f"<a href='#{esc(section_id)}'>{esc(section.get('title', section_id))}</a>")
        observations = "".join(observation_card(item) for item in section.get("observations", []))
        section_html.append(f"""
    <section id="{esc(section_id)}" class="report-section">
      <div class="section-heading"><span>{len(section_html) + 1:02}</span><div><h2>{esc(section.get('title', section_id))}</h2><p>{esc(section.get('summary', ''))}</p></div></div>
      <div class="observation-grid">{observations}</div>
    </section>""")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in spec["actions"]:
        grouped[action["theme"]].append(action)
    action_groups = []
    for theme, actions in grouped.items():
        cards = "".join(action_card(action) for action in actions)
        action_groups.append(f"<div class='action-theme'><h3>{esc(theme)}</h3>{cards}</div>")

    not_recommended = "".join(
        f"<article><h3>{esc(item.get('title', ''))}</h3><p>{esc(item.get('reason', ''))}</p></article>"
        for item in spec.get("not_recommended", [])
    )
    action_json = json.dumps(spec["actions"], ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    storage_key = f"pi-usage-audit:{report['id']}:selection"
    next_audit = spec.get("next_audit", {})

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>{esc(report.get('title', 'Pi Workflow Insights'))}</title>
<style>
:root {{ --bg:#11130f; --panel:#191c16; --panel2:#20241c; --text:#f0f1e8; --muted:#aeb5a4; --line:#343a2e; --green:#b8d77a; --amber:#e8bb70; --red:#e88678; --blue:#81b9d2; --shadow:0 18px 50px #0005; }}
* {{ box-sizing:border-box; }} html {{ scroll-behavior:smooth; }}
body {{ margin:0; background:radial-gradient(circle at 75% 0,#26301f 0,transparent 30rem),var(--bg); color:var(--text); font:16px/1.6 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
a {{ color:inherit; }} button {{ font:inherit; }}
.shell {{ max-width:1240px; margin:auto; padding:0 28px 90px; }}
.hero {{ padding:72px 0 42px; display:grid; grid-template-columns:1fr auto; gap:32px; align-items:end; border-bottom:1px solid var(--line); }}
.eyebrow {{ color:var(--green); text-transform:uppercase; letter-spacing:.16em; font-size:.75rem; font-weight:800; }}
h1 {{ font-size:clamp(2.7rem,7vw,6.4rem); line-height:.92; letter-spacing:-.065em; margin:.25rem 0 1rem; max-width:900px; }}
.subtitle {{ color:var(--muted); max-width:700px; font-size:1.1rem; }}
.period {{ text-align:right; color:var(--muted); font-size:.88rem; }} .period strong {{ color:var(--text); display:block; }}
nav {{ position:sticky; top:0; z-index:4; margin:0 -28px; padding:12px 28px; display:flex; gap:8px; overflow:auto; background:#11130fe8; backdrop-filter:blur(14px); border-bottom:1px solid var(--line); }}
nav a {{ padding:6px 12px; border-radius:999px; text-decoration:none; white-space:nowrap; color:var(--muted); }} nav a:hover {{ color:var(--text); background:var(--panel2); }}
section {{ scroll-margin-top:72px; }} #overview {{ padding:52px 0 20px; }}
.summary {{ font-size:clamp(1.25rem,2vw,1.7rem); max-width:950px; letter-spacing:-.02em; }}
.metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:32px 0; }}
.metric {{ background:var(--panel); border:1px solid var(--line); border-radius:15px; padding:20px; }} .metric strong {{ display:block; font-size:2rem; color:var(--green); }} .metric span {{ display:block; font-weight:700; }} .metric small {{ color:var(--muted); }}
.report-section {{ padding:54px 0 20px; border-top:1px solid var(--line); }}
.section-heading {{ display:grid; grid-template-columns:48px 1fr; gap:18px; align-items:start; margin-bottom:24px; }} .section-heading>span {{ color:var(--green); font:700 .8rem ui-monospace,monospace; padding-top:9px; }}
h2 {{ margin:0; font-size:clamp(1.8rem,4vw,3rem); letter-spacing:-.045em; }} .section-heading p {{ color:var(--muted); margin:.4rem 0; max-width:820px; }}
.observation-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }}
.observation {{ background:linear-gradient(145deg,var(--panel),#171914); border:1px solid var(--line); border-radius:16px; padding:22px; }} h3 {{ line-height:1.25; }} .observation h3 {{ margin:0 0 10px; }} .observation p {{ color:var(--muted); }}
.evidence {{ border-top:1px solid var(--line); margin-top:16px; padding-top:13px; font-size:.88rem; color:var(--muted); }} .evidence span {{ color:var(--blue); font-weight:800; margin-right:8px; text-transform:uppercase; letter-spacing:.08em; font-size:.7rem; }}
#actions {{ padding:56px 0 30px; border-top:1px solid var(--line); }}
.action-toolbar {{ position:sticky; top:58px; z-index:3; display:flex; flex-wrap:wrap; gap:8px; align-items:center; background:#20241cf2; border:1px solid var(--line); padding:12px; border-radius:14px; box-shadow:var(--shadow); }}
.btn {{ border:1px solid var(--line); color:var(--text); background:var(--panel); border-radius:9px; padding:8px 12px; cursor:pointer; }} .btn:hover {{ border-color:var(--green); }} .btn.primary {{ background:var(--green); color:#15180f; border-color:var(--green); font-weight:800; }} .selection-count {{ margin-left:auto; color:var(--muted); }}
.action-theme {{ margin-top:36px; }} .action-theme>h3 {{ color:var(--green); font-size:.85rem; text-transform:uppercase; letter-spacing:.12em; }}
.action-card {{ display:grid; grid-template-columns:48px 1fr; gap:6px; background:var(--panel); border:1px solid var(--line); border-radius:16px; margin:12px 0; padding:18px; transition:.18s; }} .action-card:has(input:checked) {{ border-color:#829b57; box-shadow:0 0 0 1px #829b5740; }}
.action-select {{ display:flex; justify-content:center; padding-top:5px; cursor:pointer; }} .action-checkbox {{ width:20px; height:20px; accent-color:var(--green); }}
.action-main h3 {{ margin:8px 0 5px; font-size:1.25rem; }} .action-main p {{ color:var(--muted); margin:.4rem 0; }} .action-main .recommendation {{ color:var(--text); }}
.badges {{ display:flex; flex-wrap:wrap; gap:6px; }} .badge {{ border:1px solid var(--line); border-radius:999px; padding:2px 8px; font-size:.68rem; text-transform:uppercase; letter-spacing:.08em; }} .priority-high {{ color:var(--red); }} .priority-medium {{ color:var(--amber); }} .priority-low {{ color:var(--blue); }} .status {{ color:var(--green); }} .kind {{ color:var(--muted); }}
details {{ margin-top:14px; border-top:1px solid var(--line); padding-top:10px; }} summary {{ cursor:pointer; color:var(--blue); }} details h4 {{ margin-bottom:0; }} details li {{ color:var(--muted); }}
.prompt-panel {{ margin-top:48px; background:#0c0e0b; border:1px solid var(--line); border-radius:18px; padding:22px; }} textarea {{ width:100%; min-height:300px; resize:vertical; background:#080a07; color:#dce5ce; border:1px solid var(--line); border-radius:10px; padding:16px; font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace; }} .prompt-head {{ display:flex; justify-content:space-between; gap:20px; align-items:center; }} #copy-status {{ color:var(--green); font-size:.85rem; min-height:1.3em; }}
.not-recommended {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }} .not-recommended article {{ border-left:3px solid var(--amber); padding:4px 18px; background:var(--panel); }}
footer {{ color:var(--muted); border-top:1px solid var(--line); margin-top:54px; padding:30px 0; font-size:.87rem; }} .sr-only {{ position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0; }}
@media(max-width:700px) {{ .hero {{ grid-template-columns:1fr; }} .period {{ text-align:left; }} .shell {{ padding-left:18px;padding-right:18px; }} nav {{ margin-left:-18px;margin-right:-18px;padding-left:18px; }} .action-toolbar {{ top:54px; }} .selection-count {{ width:100%; margin-left:0; }} }}
@media print {{ nav,.action-toolbar,.action-select,.prompt-head button {{ display:none!important; }} body {{ background:white;color:#111; }} .shell {{ max-width:none;padding:0; }} .metric,.observation,.action-card,.prompt-panel,.not-recommended article {{ background:white;color:#111;border-color:#bbb;box-shadow:none;break-inside:avoid; }} p,.metric small,.action-main p,details li,footer {{ color:#333!important; }} textarea {{ color:#111;background:white; }} }}
</style>
</head>
<body>
<div class="shell">
  <header class="hero">
    <div><div class="eyebrow">Pi usage audit</div><h1>{esc(report.get('title', 'Pi Workflow Insights'))}</h1><p class="subtitle">{esc(report.get('subtitle', ''))}</p></div>
    <div class="period"><strong>{esc(period['start'])}</strong>through <strong>{esc(period['end'])}</strong><br>{esc(period['selection'])}</div>
  </header>
  <nav>{''.join(nav_html)}<a href="#actions">Actions</a><a href="#apply-prompt">Apply prompt</a></nav>
  <main>
    <section id="overview"><div class="eyebrow">Executive summary</div><p class="summary">{esc(spec['executive_summary'])}</p><div class="metrics">{metrics}</div><p class="evidence">{esc(report.get('methodology', ''))}</p></section>
    {''.join(section_html)}
    <section id="actions">
      <div class="section-heading"><span>→</span><div><h2>Recommended actions</h2><p>Select only the changes you want. The report generates an approval prompt; it never changes your setup.</p></div></div>
      <div class="action-toolbar"><button class="btn" id="select-all">Select all</button><button class="btn" id="select-none">Select none</button><button class="btn" id="select-pending">Pending only</button><button class="btn" onclick="window.print()">Print</button><span class="selection-count" id="selection-count"></span></div>
      {''.join(action_groups)}
      <div class="prompt-panel" id="apply-prompt"><div class="prompt-head"><div><div class="eyebrow">Generated approval prompt</div><h3>Apply selected improvements</h3></div><button class="btn primary" id="copy-prompt">Copy prompt</button></div><textarea id="prompt-output" readonly></textarea><div id="copy-status" aria-live="polite"></div></div>
    </section>
    <section class="report-section"><div class="section-heading"><span>×</span><div><h2>Not recommended</h2><p>Ideas intentionally excluded or deferred.</p></div></div><div class="not-recommended">{not_recommended}</div></section>
  </main>
  <footer><strong>Next audit:</strong> {esc(next_audit.get('recommendation', ''))}<br><strong>Default next start:</strong> {esc(next_audit.get('default_start', period['end']))}<br>This self-contained report makes no network requests. Checkbox choices remain in this browser only.</footer>
</div>
<script id="action-data" type="application/json">{action_json}</script>
<script>
(() => {{
  const actions = JSON.parse(document.getElementById('action-data').textContent);
  const byId = new Map(actions.map(action => [action.id, action]));
  const boxes = [...document.querySelectorAll('.action-checkbox')];
  const output = document.getElementById('prompt-output');
  const count = document.getElementById('selection-count');
  const status = document.getElementById('copy-status');
  const storageKey = {json.dumps(storage_key)};
  try {{
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (Array.isArray(saved)) boxes.forEach(box => box.checked = saved.includes(box.value));
  }} catch (_) {{}}
  function promptFor(selected) {{
    if (!selected.length) return 'Select one or more actions to generate an implementation prompt.';
    const lines = [
      'Apply only the following approved Pi workflow improvements.',
      '',
      'Before changing anything, inspect the current configuration and relevant project state. Reuse or extend existing instructions, prompts, skills, scripts, or extensions instead of duplicating them. Preserve unrelated changes. If an approved action conflicts with current state or has already been implemented, report that clearly and ask before replacing or removing anything.',
      '',
      'Approved actions:'
    ];
    selected.forEach((action, index) => {{
      lines.push('', `${{index + 1}}. ${{action.title}} [${{action.kind}}; current status: ${{action.status}}]`, action.recommendation, `Rationale: ${{action.rationale}}`, 'Implementation:');
      action.implementation.forEach(step => lines.push(`- ${{step}}`));
    }});
    lines.push('', 'After implementation, validate every changed resource, report exact file paths, state what was reused versus introduced, and list anything deliberately left unchanged. Do not implement unselected report actions.');
    return lines.join('\\n');
  }}
  function update() {{
    const ids = boxes.filter(box => box.checked).map(box => box.value);
    const selected = ids.map(id => byId.get(id)).filter(Boolean);
    output.value = promptFor(selected);
    count.textContent = `${{selected.length}} of ${{actions.length}} selected`;
    try {{ localStorage.setItem(storageKey, JSON.stringify(ids)); }} catch (_) {{}}
    status.textContent = '';
  }}
  boxes.forEach(box => box.addEventListener('change', update));
  document.getElementById('select-all').addEventListener('click', () => {{ boxes.forEach(box => box.checked = true); update(); }});
  document.getElementById('select-none').addEventListener('click', () => {{ boxes.forEach(box => box.checked = false); update(); }});
  document.getElementById('select-pending').addEventListener('click', () => {{ boxes.forEach(box => box.checked = byId.get(box.value)?.status === 'pending'); update(); }});
  document.getElementById('copy-prompt').addEventListener('click', async () => {{
    output.focus(); output.select();
    let copied = false;
    try {{ await navigator.clipboard.writeText(output.value); copied = true; }} catch (_) {{ try {{ copied = document.execCommand('copy'); }} catch (_) {{}} }}
    status.textContent = copied ? 'Copied to clipboard.' : 'Clipboard access was blocked. The prompt is selected; copy it manually.';
  }});
  update();
}})();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="report specification JSON")
    parser.add_argument("--output", required=True, help="HTML output path")
    parser.add_argument("--set-latest", action="store_true", help="advance usage-audits/latest.json to this report cutoff")
    args = parser.parse_args()
    try:
        spec_path = Path(args.spec).expanduser().resolve()
        output = Path(args.output).expanduser().resolve()
        spec = json.loads(spec_path.read_text())
        rendered = render(spec)
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(output.parent, stat.S_IRWXU)
        output.write_text(rendered)
        os.chmod(output, stat.S_IRUSR | stat.S_IWUSR)
        result: dict[str, Any] = {"report": str(output), "latest_updated": False}
        if args.set_latest:
            config_dir = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent")).expanduser().resolve()
            audit_root = config_dir / "usage-audits"
            audit_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            manifest = {
                "schema_version": 1,
                "report_id": spec["report"]["id"],
                "report_path": str(output),
                "generated_at": spec["report"].get("generated_at"),
                "period": spec["report"]["period"],
                "action_statuses": {action["id"]: action["status"] for action in spec["actions"]},
            }
            latest = audit_root / "latest.json"
            temporary = audit_root / ".latest.json.tmp"
            temporary.write_text(json.dumps(manifest, indent=2))
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
            temporary.replace(latest)
            result["latest_updated"] = True
            result["latest_manifest"] = str(latest)
        print(json.dumps(result, indent=2))
    except (OSError, json.JSONDecodeError, SpecError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
