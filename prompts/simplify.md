---
description: Perform an independent read-only maintainability review
argument-hint: "[uncommitted|branch <ref>|range <a>..<b>|PR <number>]"
---
Perform an independent, read-only maintainability review of: ${@:-uncommitted changes}

Assume correctness review is separate. Do not modify files, Git state, issue trackers, or external systems.

Read the repository instructions. Resolve and state the exact base, head, and diff before reviewing. Trace the closest reusable code, callers, tests, validation, and expected direction of change.

Look for clearly actionable improvements involving:

- duplicated behavior or missed reuse;
- dead, unreachable, obsolete, or compatibility-only code without a current requirement;
- unnecessary complexity, indirection, abstraction, or configuration;
- incorrect abstraction level or misplaced responsibility;
- domain states represented with loose objects, strings, dictionaries, unrelated options, or repeated runtime checks;
- weak module boundaries, error modeling, naming, or readability;
- unnecessary allocations, dynamic dispatch, dependencies, or excessive dependency features;
- algorithmic or allocation problems supported by evidence.

Do not recommend speculative micro-optimizations, broad rewrites, premature generalization, or changes that weaken contracts, typing, tests, security, lifecycle guarantees, or required compatibility. Separate safe in-scope simplifications from deferred structural refactors.

Report recommendations in value order with locations, rationale, risk, and the smallest safe change. If the implementation is already appropriately simple and maintainable, say so explicitly.
