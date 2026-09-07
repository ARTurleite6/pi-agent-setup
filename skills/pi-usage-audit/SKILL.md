---
name: pi-usage-audit
description: Audits saved Pi sessions and current customizations to find repeated requests, corrections, friction, and opportunities for prompts, skills, instructions, or workflow changes. Produces a private self-contained interactive HTML report. Invoke explicitly for periodic workflow analysis.
disable-model-invocation: true
---

# Pi usage audit

Audit Pi usage without exposing assistant thinking, images, raw tool results, or full source/file contents. This skill is manually invoked because session history may be sensitive.

Resolve script paths relative to this skill directory.

## Default period

- If the user supplies a range, honor it.
- Otherwise, read `~/.pi/agent/usage-audits/latest.json` and begin immediately after that report's `period.end` cutoff.
- If no valid prior report exists, use the last 30 days.
- Always state whether the period came from an explicit request, the previous report, or the first-run fallback.
- Scan all session files but include messages by their own timestamp, so newly appended messages in an older session are not missed.

## Privacy boundary

The extractor must:

- include sanitized user text only;
- never include assistant text or thinking;
- never include image data;
- include tool names and error counts but not tool arguments or result contents;
- replace the home directory with `~`;
- redact likely credentials and secrets;
- replace fenced code blocks and large data payloads with placeholders;
- bound prompt excerpts;
- keep reports local under `~/.pi/agent/usage-audits/` with user-only permissions.

Warn the user that sanitized report content is still sent to the selected model provider when the agent analyzes it. Use a local model if the material must not leave the machine.

## Extract

Run one of:

```bash
python3 scripts/extract-usage.py
python3 scripts/extract-usage.py --days 30
python3 scripts/extract-usage.py --since 2026-08-01T00:00:00Z --until 2026-09-01T00:00:00Z
python3 scripts/extract-usage.py --project smide-cad-runtime
```

The command prints the extraction JSON path. Read that bounded JSON and inspect the names and descriptions of the currently installed instructions, prompts, skills, extensions, and packages when needed. Do not load unrelated session or tool-result content manually.

## Analyze

Identify evidence-backed themes including:

- repeated task categories and exact repeated requests;
- corrections, scope reductions, and mode confusion;
- requests repeatedly turned into next-session prompts;
- worktree, Git, review, testing, and documentation patterns;
- repeated failures, aborts, opaque iteration, and shared-resource contention;
- session-length and cost concentration;
- existing customization that already addresses a pattern;
- missing or overlapping global/project instructions, prompts, skills, and extensions.

Map recommendations to the smallest suitable mechanism:

- persistent personal convention -> global `AGENTS.md`;
- repository convention -> project `AGENTS.md`;
- reusable wording -> prompt template;
- multi-step workflow with scripts or references -> skill;
- deterministic tool, UI, event, or policy enforcement -> extension or CLI;
- behavior change requiring no configuration -> working-practice recommendation.

Prefer extending an existing customization over creating a duplicate. Explicitly identify recommendations that are already implemented, pending, declined, or superseded. Do not apply any recommendation during the audit.

## Build the report specification

Write a JSON file following `references/report-spec.md`. Organize observations and actions by theme. Preserve the level of detail needed to explain why each recommendation exists, but do not embed all extracted prompts.

Every action needs:

- stable ID;
- theme;
- priority;
- status;
- concise recommendation;
- evidence;
- rationale;
- concrete implementation steps;
- whether it should be selected by default.

The generated apply prompt must instruct the next agent to inspect current state, preserve unrelated changes, reuse existing customization, and request clarification on conflicts.

## Render HTML

```bash
python3 scripts/render-report.py \
  --spec <report-spec.json> \
  --output <report-directory>/report.html \
  --set-latest
```

The report must be self-contained and make no network requests. It provides:

- thematic navigation and focused sections;
- summary metrics and evidence;
- recommendation status and priority;
- selectable individual actions;
- select-all, select-none, and pending-only controls;
- a generated apply prompt;
- copy-prompt fallback that works for local `file://` pages;
- print support.

Only use `--set-latest` for a completed audit the user accepts as the new cutoff. Iterative previews should omit it so they do not advance the next default period.

## Finish

Print:

1. the exact HTML report path;
2. the audited period and how it was chosen;
3. whether it became the latest audit baseline;
4. the next default audit start;
5. a reminder that selecting actions in HTML does not mutate the setup—it only generates a prompt for a later approved session.
