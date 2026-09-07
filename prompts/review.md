---
description: Perform an independent read-only correctness review
argument-hint: "[uncommitted|branch <ref>|range <a>..<b>|PR <number>]"
---
Perform an independent, read-only correctness review of: ${@:-uncommitted changes}

Do not modify files, Git state, issue trackers, or external systems.

Read the repository instructions. Resolve and state the exact base, head, and diff before reviewing; if the requested target is invalid or materially ambiguous, stop and ask rather than widening scope. Inspect surrounding production and test code only as needed to validate findings.

Focus on actionable:

- correctness bugs and regressions;
- security, authorization, lifecycle, concurrency, and stale-state violations;
- contract, schema, serialization, and compatibility errors;
- error-handling and fail-open behavior;
- unmet requirements or plan commitments;
- missing tests that would expose a concrete failure.

Report findings in severity order. For each finding include the location, failure scenario, impact, evidence, and smallest safe fix. Avoid speculative style observations and maintainability-only suggestions. If no actionable correctness findings exist, say so explicitly. End with remaining verification uncertainty.
