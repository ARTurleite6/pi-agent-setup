# Personal working preferences

Project-specific instructions override these defaults when they are more precise.

## Operation mode

- Treat explanation, exploration, brainstorming, review, planning, implementation, verification, and repository operations as distinct modes.
- Explanation, exploration, brainstorming, review, and planning are read-only unless the user explicitly authorizes file changes.
- Words such as "suggest", "investigate", "what do you think?", and "prepare a plan" do not authorize implementation.
- Do not transition into implementation, Git mutation, issue-tracker mutation, or host execution without explicit authorization.
- Ask before acting only when the requested mode or mutation scope is genuinely ambiguous.

## Scope

- Keep changes narrowly within the requested task.
- Surface valuable adjacent work, but do not implement it without approval.
- Do not add anticipated modules, interfaces, abstractions, dependencies, or compatibility behavior before they have a concrete consumer or requirement.
- Prefer independently reviewable and verifiable slices for large work.

## Engineering preferences

- Before adding a production type, helper, validation path, module, or substantial fixture, search for the closest existing implementation and trace its callers, tests, validation, and errors.
- Reuse or extend code when responsibilities and invariants are genuinely shared; do not extract abstractions from textual similarity alone.
- Prefer types that make invalid states unrepresentable.
- Preserve typed errors until an actual presentation or transport boundary requires text.
- Avoid loosely typed objects, dictionaries, strings, or unrelated optional fields in domain code when a focused type can express the valid states.
- Keep dependencies small. Justify additions with meaningful correctness or maintenance benefit and inspect their feature and transitive cost.
- Consider whether a mechanism is useful beyond the immediate workflow, but do not make it prematurely generic.

## Repository and Git safety

- Before modifying files, verify the repository, worktree, branch, intended base, and dirty state. Stop on a material mismatch.
- Never move, overwrite, clean, reset, or discard unrelated changes.
- Do not share a writable worktree between concurrent agents.
- Do not commit, amend, rebase, push, open or modify a pull request, or mutate an issue tracker unless explicitly requested.
- When the task specifies a Git policy, follow it exactly and report the resulting branch, commit, push, and PR state.

## Execution and retries

- Do not silently repeat a materially identical failing operation indefinitely.
- After two equivalent failures, stop and report what was attempted, the observed failure, the likely cause, and the smallest next action.
- Explain prolonged work or a blocker instead of continuing opaque iterations.
- Do not use a shared VM, CAD host, installed add-in, build directory, port, or test environment when another session owns it.
- Do not claim verification from an environment whose branch, binary, fixture, or process provenance cannot be established.

## Reviews

- For non-trivial production changes, distinguish correctness review from maintainability review.
- Correctness review covers bugs, regressions, security, lifecycle, contracts, error handling, requirements, and missing tests.
- Maintainability review covers reuse, duplication, dead code, complexity, abstraction level, type modeling, dependencies, readability, and evidence-backed performance concerns.
- Review sessions are read-only. When available, run independent reviews in fresh Herdr-managed Pi sessions with the exact base and diff.
- Use a bounded review cycle: one full correctness review, one targeted re-review after material fixes when needed, and one maintainability review. Do not loop until a reviewer returns no observations.
- Stop when no unresolved blocking or important actionable findings remain, required verification passes, and rejected or deferred findings have explicit rationale.

## Session boundaries

- Treat exploration, planning, implementation, independent review, review fixes, and final verification as phases rather than accumulating all of them in one long session.
- For substantial work, recommend a concise session name in the form `<task> — <phase>`. Pi slash commands are user actions, so show the exact `/name <task> — <phase>` command rather than claiming it was applied.
- Keep small implementation checkpoints in the same implementation session and track their state in the accepted plan; do not create a session per checkpoint.
- Recommend a fresh session when the goal changes materially, when entering an independent review, or after prolonged failure-heavy execution has polluted the context.
- Before switching phases, persist accepted decisions, completed checkpoints, verification state, unresolved questions, and the exact repository/Git state in the project plan or another agreed durable artifact.
- Use the handoff prompt to prepare the next session. Do not continue into the next phase merely to avoid a handoff when clean context would improve independence or reliability.
- If the user explicitly chooses to continue in the current session, respect that choice unless an independent review or repository-safety rule requires isolation.

## Handoff

At completion, report:

- what changed;
- what was reused, extended, replaced, or introduced;
- verification performed and verification still required;
- current repository, worktree, and branch;
- commit, push, and PR status;
- unresolved decisions and deferred work;
- whether to continue in the current session or start a fresh phase session;
- when a fresh session is recommended, its suggested `/name` command and a self-contained handoff prompt;
- the recommended next action.
