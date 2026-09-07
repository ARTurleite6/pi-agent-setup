---
description: Implement an accepted plan with repository and review safeguards
argument-hint: "<plan-file> [additional constraints]"
---
Implement the accepted plan at $1.

Additional constraints: ${@:2}

Before modifying anything:

1. Read the repository instructions and the complete plan and follow their references.
2. Verify the repository, worktree, branch, intended base, HEAD, and dirty state.
3. Stop and report any material mismatch or unrelated changes that make the requested work unsafe.
4. Identify and trace the closest existing code to reuse or extend.
5. Confirm the task's Git policy. Do not infer permission to commit, push, rebase, or open a PR.
6. Treat this as the implementation phase. Suggest `/name <task> — implementation` if a clear phase name has not been established; do not claim to execute the slash command.

Implement only the accepted scope in independently verifiable checkpoints. Keep the plan status current when the repository expects that. Do not silently add adjacent work or anticipated abstractions. After two materially equivalent failures, stop and diagnose instead of repeatedly retrying.

Run applicable focused verification while iterating. Before final expensive or host-native verification, complete the plan's bounded correctness and maintainability review gates. Independent review sessions must be fresh, read-only, Herdr-managed when available, and scoped to the exact base and diff. The implementation session owns finding triage and fixes.

Do not use shared native resources unless their ownership and branch/binary provenance are established. Before recommending a transition to independent review or another phase, persist accepted decisions, completed checkpoints, verification state, unresolved questions, and exact repository/Git state in the plan or agreed durable artifact. Keep small implementation checkpoints in this session rather than creating a session for each one.

At handoff, report changes, reuse, verification, findings disposition, worktree and branch, Git/PR state, limitations, whether a fresh phase session is recommended, its suggested `/name` command, and the recommended next action.
