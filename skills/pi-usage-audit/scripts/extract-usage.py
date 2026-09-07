#!/usr/bin/env python3
"""Create a bounded, privacy-preserving extraction from saved Pi sessions."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc
MAX_EXCERPT = 600
MAX_EXCERPTS = 500

PATTERNS = {
    "explanation_or_learning": r"\b(explain|what does|what is|why (?:do|does|did|is|was|are|would)|how (?:does|do|is|are|would|can|could))\b",
    "planning_or_architecture": r"\b(plan|planning|architecture|design|brainstorm|strategy|approach)\b",
    "review_or_simplification": r"\b(review|simplif|audit|findings|code quality|maintainab)\b",
    "next_session_prompt": r"\b(?:give|create|write).{0,40}\bprompt\b|\bprompt.{0,40}(?:next|another) session\b",
    "cross_session_decision": r"\banother (?:pi )?session\b|\bnew session\b|\bcontinue in this session\b|\bswitch session\b|\bspawn.{0,20}(?:agent|instance)\b",
    "persist_to_documentation": r"\b(?:store|write|keep|put|add|update).{0,40}\b(?:file|document|docs|plan|agents\.md)\b",
    "worktree_or_isolation": r"\bworktree\b|\bseparate branch\b|\banother branch\b",
    "git_lifecycle": r"\b(commit|push|pull request|pr|rebase|branch|stacked)\b",
    "reuse_or_genericity": r"\b(reus|already exists|generic|other (?:features|use cases|usages)|not only|code quality)\b",
    "scope_restraint": r"\b(do not|don't|for now|defer|only|without|keep it narrow|not needed|not necessary)\b",
    "continuation_handshake": r"^(?:nice[, .]*|ok(?:ay)?[, .]*|please )?(?:continue|go (?:on|ahead)|do it|proceed|ready|done|try again)(?:\s+(?:now|please))?[.! ]*$",
    "correction_or_redirection": r"\b(no[, ]|not what|instead|actually|i asked|why did|still happening|don't|do not|rather than|without asking)\b",
}

SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_ -]?key|token|password|secret|authorization)(\s*[:=]\s*)[^\s,;]+"), r"\1\2<REDACTED>"),
    (re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b"), "<REDACTED_SECRET>"),
]


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def parse_time(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def message_time(message: dict[str, Any], entry: dict[str, Any]) -> datetime | None:
    timestamp = message.get("timestamp")
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp / 1000, UTC)
    entry_timestamp = entry.get("timestamp")
    if isinstance(entry_timestamp, str):
        try:
            return parse_time(entry_timestamp)
        except ValueError:
            return None
    return None


def text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def sanitize(text: str, home: Path) -> str:
    value = text.replace(str(home), "~")
    for pattern, replacement in SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    value = re.sub(r"(?s)```.*?```", "<CODE_BLOCK>", value)
    value = re.sub(r"data:[^\s]{200,}", "<DATA_PAYLOAD>", value)
    value = re.sub(r"[A-Za-z0-9+/=]{500,}", "<LARGE_ENCODED_PAYLOAD>", value)
    return re.sub(r"\s+", " ", value).strip()


def bounded_excerpt(value: str) -> str:
    if len(value) <= MAX_EXCERPT:
        return value
    return value[: MAX_EXCERPT - 1].rstrip() + "…"


def load_latest(audit_root: Path) -> dict[str, Any] | None:
    path = audit_root / "latest.json"
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    end = value.get("period", {}).get("end")
    if not isinstance(end, str):
        return None
    try:
        parse_time(end)
    except ValueError:
        return None
    value["manifest_path"] = str(path)
    return value


def choose_period(args: argparse.Namespace, audit_root: Path) -> tuple[datetime, datetime, str, dict[str, Any] | None]:
    end = parse_time(args.until) if args.until else utc_now()
    latest = load_latest(audit_root)
    if args.since:
        start = parse_time(args.since)
        selection = "explicit since/until range"
    elif args.days is not None:
        start = end - timedelta(days=args.days)
        selection = f"explicit last {args.days} days"
    elif latest:
        start = parse_time(latest["period"]["end"])
        selection = "incremental range from previous accepted report"
    else:
        start = end - timedelta(days=30)
        selection = "first-run 30-day fallback"
    if start >= end:
        raise ValueError("audit start must be earlier than audit end")
    return start, end, selection, latest


def in_period(value: datetime | None, start: datetime, end: datetime) -> bool:
    return value is not None and start < value <= end


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower())


def resource_description(path: Path) -> str | None:
    try:
        text = path.read_text(errors="replace")[:4096]
    except OSError:
        return None
    match = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def inventory(config_dir: Path, cwd: Path) -> dict[str, Any]:
    resources: dict[str, Any] = {}
    for directory, pattern in [("prompts", "*.md"), ("extensions", "**/*"), ("themes", "*.json")]:
        root = config_dir / directory
        files = [p for p in root.glob(pattern) if p.is_file()] if root.exists() else []
        resources[directory] = [str(p.relative_to(config_dir)) for p in sorted(files)]

    skills = []
    for skill_file in sorted((config_dir / "skills").glob("**/SKILL.md")) if (config_dir / "skills").exists() else []:
        skills.append({"path": str(skill_file.relative_to(config_dir)), "description": resource_description(skill_file)})
    resources["skills"] = skills

    instruction_files = []
    global_agents = config_dir / "AGENTS.md"
    if global_agents.exists():
        instruction_files.append(str(global_agents))
    current = cwd.resolve()
    lineage = [current, *current.parents]
    for directory in reversed(lineage):
        for name in ("AGENTS.override.md", "AGENTS.md", "CLAUDE.md"):
            candidate = directory / name
            if candidate.exists() and str(candidate) not in instruction_files:
                instruction_files.append(str(candidate))
                break
    resources["instruction_files"] = instruction_files

    settings_path = config_dir / "settings.json"
    packages: list[str] = []
    try:
        settings = json.loads(settings_path.read_text())
        packages = [str(item) for item in settings.get("packages", [])]
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    resources["packages"] = packages
    return resources


def extract(args: argparse.Namespace) -> Path:
    home = Path.home()
    config_dir = Path(args.config_dir or os.environ.get("PI_CODING_AGENT_DIR", home / ".pi/agent")).expanduser().resolve()
    session_root = Path(args.session_dir or os.environ.get("PI_CODING_AGENT_SESSION_DIR", config_dir / "sessions")).expanduser().resolve()
    audit_root = config_dir / "usage-audits"
    audit_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(audit_root, stat.S_IRWXU)

    start, end, selection, latest = choose_period(args, audit_root)
    project_filter = args.project.lower() if args.project else None

    roles: Counter[str] = Counter()
    projects: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    tool_errors: Counter[str] = Counter()
    models: Counter[str] = Counter()
    stop_reasons: Counter[str] = Counter()
    pattern_hits: dict[str, list[int]] = {name: [] for name in PATTERNS}
    prompts: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []
    total_cost = 0.0
    total_tokens = 0

    files = sorted(session_root.rglob("*.jsonl")) if session_root.exists() else []
    for session_file in files:
        header: dict[str, Any] = {}
        session_prompts: list[dict[str, Any]] = []
        session_tools = 0
        session_errors = 0
        session_cost = 0.0
        session_tokens = 0
        first_in_period: datetime | None = None
        last_in_period: datetime | None = None

        with session_file.open(errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") == "session":
                    header = entry
                    continue
                if entry.get("type") != "message":
                    continue
                message = entry.get("message") or {}
                timestamp = message_time(message, entry)
                if not in_period(timestamp, start, end):
                    continue

                cwd = str(header.get("cwd", "unknown"))
                project = Path(cwd).name or "unknown"
                if project_filter and project_filter not in project.lower() and project_filter not in cwd.lower():
                    continue

                first_in_period = timestamp if first_in_period is None else min(first_in_period, timestamp)
                last_in_period = timestamp if last_in_period is None else max(last_in_period, timestamp)
                role = str(message.get("role", "unknown"))
                roles[role] += 1

                if role == "user":
                    analysis_text = sanitize(text_content(message.get("content")), home)
                    if analysis_text:
                        session_prompts.append(
                            {
                                "entry_id": entry.get("id"),
                                "timestamp": iso(timestamp),
                                "text": bounded_excerpt(analysis_text),
                                "_analysis_text": analysis_text,
                            }
                        )
                elif role == "assistant":
                    provider = message.get("provider", "unknown")
                    model = message.get("model", "unknown")
                    models[f"{provider}/{model}"] += 1
                    stop_reasons[str(message.get("stopReason", "unknown"))] += 1
                    usage = message.get("usage") or {}
                    tokens = int(usage.get("totalTokens") or 0)
                    cost = float((usage.get("cost") or {}).get("total") or 0)
                    session_tokens += tokens
                    session_cost += cost
                    for block in message.get("content") or []:
                        if isinstance(block, dict) and block.get("type") == "toolCall":
                            tools[str(block.get("name", "unknown"))] += 1
                            session_tools += 1
                elif role == "toolResult" and message.get("isError"):
                    name = str(message.get("toolName", "unknown"))
                    tool_errors[name] += 1
                    session_errors += 1

        if first_in_period is None:
            continue
        cwd = str(header.get("cwd", "unknown"))
        project = Path(cwd).name or "unknown"
        projects[project] += 1
        session_index = len(sessions)
        session_record = {
            "index": session_index,
            "session_id": header.get("id"),
            "file": str(session_file.relative_to(session_root)),
            "project": project,
            "first_message": iso(first_in_period),
            "last_message": iso(last_in_period or first_in_period),
            "user_prompts": len(session_prompts),
            "tool_calls": session_tools,
            "tool_errors": session_errors,
            "tokens": session_tokens,
            "cost": round(session_cost, 6),
        }
        sessions.append(session_record)
        total_cost += session_cost
        total_tokens += session_tokens
        for index, prompt in enumerate(session_prompts):
            analysis_text = prompt.pop("_analysis_text")
            record = {
                "session": session_index,
                "position": index,
                "project": project,
                **prompt,
            }
            prompt_index = len(prompts)
            prompts.append(record)
            for name, expression in PATTERNS.items():
                if re.search(expression, analysis_text, re.IGNORECASE):
                    pattern_hits[name].append(prompt_index)

    exact = Counter(normalized(prompt["text"]) for prompt in prompts)
    exact_examples = {normalized(prompt["text"]): prompt["text"] for prompt in prompts}
    lengths = sorted(len(prompt["text"]) for prompt in prompts)

    pattern_summary = {
        name: {
            "prompts": len(indices),
            "sessions": len({prompts[index]["session"] for index in indices}),
            "examples": [prompts[index]["text"] for index in indices[:8]],
        }
        for name, indices in pattern_hits.items()
    }

    extraction = {
        "schema_version": 1,
        "privacy": {
            "assistant_text_included": False,
            "assistant_thinking_included": False,
            "images_included": False,
            "tool_arguments_included": False,
            "tool_result_contents_included": False,
            "user_text": "sanitized and bounded excerpts",
        },
        "period": {
            "start": iso(start),
            "end": iso(end),
            "selection": selection,
            "start_exclusive": True,
            "end_inclusive": True,
        },
        "previous_report": latest,
        "filters": {"project": args.project},
        "summary": {
            "session_files_scanned": len(files),
            "sessions_in_period": len(sessions),
            "user_prompts": len(prompts),
            "roles": dict(roles),
            "projects": dict(projects),
            "tools": dict(tools),
            "tool_errors": dict(tool_errors),
            "models": dict(models),
            "stop_reasons": dict(stop_reasons),
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "median_prompt_excerpt_length": lengths[len(lengths) // 2] if lengths else 0,
            "p90_prompt_excerpt_length": lengths[int(0.9 * (len(lengths) - 1))] if lengths else 0,
        },
        "patterns": pattern_summary,
        "exact_repeats": [
            {"count": count, "text": exact_examples[key]}
            for key, count in exact.most_common(50)
            if key and count > 1
        ],
        "highest_cost_sessions": sorted(sessions, key=lambda item: item["cost"], reverse=True)[:20],
        "highest_error_sessions": sorted(sessions, key=lambda item: item["tool_errors"], reverse=True)[:20],
        "prompt_excerpts": prompts[:MAX_EXCERPTS],
        "customization_inventory": inventory(config_dir, Path.cwd()),
    }

    report_id = end.strftime("%Y-%m-%dT%H-%M-%SZ")
    report_dir = audit_root / report_id
    suffix = 1
    while report_dir.exists():
        report_dir = audit_root / f"{report_id}-{suffix}"
        suffix += 1
    report_dir.mkdir(mode=0o700)
    output = Path(args.output).expanduser().resolve() if args.output else report_dir / "extraction.json"
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.write_text(json.dumps(extraction, indent=2))
    os.chmod(output, stat.S_IRUSR | stat.S_IWUSR)
    print(json.dumps({"extraction": str(output), "report_directory": str(output.parent), "period": extraction["period"]}, indent=2))
    return output


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    period = parser.add_mutually_exclusive_group()
    period.add_argument("--days", type=int, help="explicit number of days ending at --until or now")
    period.add_argument("--since", help="explicit exclusive ISO-8601 start")
    parser.add_argument("--until", help="inclusive ISO-8601 end (default: now)")
    parser.add_argument("--project", help="case-insensitive project path/name substring")
    parser.add_argument("--config-dir", help="Pi configuration directory")
    parser.add_argument("--session-dir", help="Pi session directory")
    parser.add_argument("--output", help="explicit extraction JSON path")
    args = parser.parse_args()
    if args.days is not None and args.days <= 0:
        parser.error("--days must be greater than zero")
    return args


def main() -> int:
    try:
        extract(arguments())
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
