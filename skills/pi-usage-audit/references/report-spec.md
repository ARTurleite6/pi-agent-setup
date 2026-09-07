# Report specification

`render-report.py` accepts one JSON object with this shape:

```json
{
  "report": {
    "id": "2026-09-05-workflow-audit",
    "title": "Pi Workflow Insights",
    "subtitle": "Patterns and recommended improvements",
    "generated_at": "2026-09-05T18:30:00Z",
    "period": {
      "start": "2026-08-26T00:00:00Z",
      "end": "2026-09-05T18:30:00Z",
      "selection": "first-run fallback"
    },
    "previous_report": null,
    "methodology": "Privacy-preserving extraction summary."
  },
  "executive_summary": "Markdown-free plain text summary.",
  "metrics": [
    {"label": "Sessions", "value": "97", "detail": "Saved Pi sessions"}
  ],
  "sections": [
    {
      "id": "workflow",
      "title": "Workflow patterns",
      "summary": "Plain text thematic summary.",
      "observations": [
        {
          "title": "Repeated planning lifecycle",
          "evidence": "Observed in 48 sessions.",
          "interpretation": "The lifecycle should be encoded once."
        }
      ]
    }
  ],
  "actions": [
    {
      "id": "global-instructions",
      "theme": "Instructions",
      "title": "Add concise personal defaults",
      "priority": "high",
      "status": "pending",
      "kind": "AGENTS.md",
      "recommendation": "Create a global instruction file.",
      "rationale": "The same constraints are repeatedly restated.",
      "evidence": ["143 scope-restraint prompts across 60 sessions."],
      "implementation": ["Inspect existing global instructions.", "Add only missing personal defaults."],
      "selected_by_default": true
    }
  ],
  "not_recommended": [
    {
      "title": "Unbounded review loops",
      "reason": "They do not have a stable stopping condition."
    }
  ],
  "next_audit": {
    "recommendation": "Run again after two to four weeks.",
    "default_start": "2026-09-05T18:30:00Z"
  }
}
```

## Constraints

- All displayed values are treated as untrusted text and escaped by the renderer.
- IDs must contain only lowercase ASCII letters, numbers, and hyphens.
- Priorities: `high`, `medium`, `low`.
- Suggested statuses: `pending`, `implemented`, `adopted`, `declined`, `deferred`, `superseded`.
- Keep metrics concise; put nuance in sections.
- Use stable action IDs across reports so comparisons remain meaningful.
- Evidence should be bounded summaries, not raw sensitive prompts.
- `period.end` is the incremental cutoff written to `latest.json` when `--set-latest` is used.
