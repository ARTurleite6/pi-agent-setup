---
description: Prepare a read-only implementation plan with review gates
argument-hint: "<task>"
---
Prepare an implementation plan for: $@

Do not modify production code or mutate Git, issue trackers, or external systems. Writing a plan file requires explicit authorization.

Read the repository instructions and relevant architecture, ADR, roadmap, testing, verification, and provider documentation. Inspect the current implementation, callers, tests, validation, and error handling. Do not infer a settled decision where the project leaves one unresolved.

Include:

- current state and exact problem;
- scope and explicit non-goals;
- assumptions and questions requiring a decision;
- a reuse audit classifying substantial components as reuse, extend, replace, or genuinely new;
- why each genuinely new component cannot safely reuse the closest candidate;
- implementation checkpoints and dependency order;
- testing and verification at each applicable layer;
- dependency, migration, compatibility, and rollback concerns;
- recommended branch, base, worktree, commit, and PR structure;
- recommended phase boundaries, with suggested `<task> — <phase>` session names;
- what durable plan state must be updated before each phase handoff;
- risks and deferrable follow-up work.

For non-trivial production work, include this bounded review gate:

1. Complete implementation and focused fast tests.
2. Run an independent, read-only correctness review in a fresh Herdr-managed Pi session against the exact verified base and diff.
3. Triage findings as accepted blocking, accepted non-blocking, deferred, or rejected with rationale.
4. Fix accepted findings in the implementation session.
5. If fixes are material, run one targeted re-review of the original findings and resulting changes.
6. Run a separate read-only maintainability review covering reuse, duplication, dead code, complexity, abstraction level, type modeling, dependencies, readability, and evidence-backed performance concerns.
7. Apply only clearly beneficial, scope-preserving simplifications.
8. Run complete required verification after all review-driven changes.
9. Stop when no unresolved blocking or important actionable findings remain; do not run an unbounded review/fix loop.

Use intermediate independent reviews only for difficult-to-reverse contracts, schemas, security or lifecycle boundaries, cross-language wire boundaries, mutation semantics, migration strategies, or foundational abstractions. Do not add a full review after every checkpoint.

Keep small checkpoints together in one implementation session. Recommend a fresh named session when moving from exploration or planning into implementation, when beginning an independent review, or after prolonged failure-heavy execution. Before such a transition, require accepted decisions, checkpoint state, verification state, unresolved questions, and exact repository/Git state to be persisted in the plan.
