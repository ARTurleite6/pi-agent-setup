---
description: Assess whether the current task is ready for handoff or PR
argument-hint: "[constraints]"
---
Assess whether the current task is complete and ready for handoff or PR.

Constraints: ${@:-none}

Do not modify files, Git state, issue trackers, or external systems. Do not add new scope merely because an improvement is possible.

Check:

- accepted plan, requirements, checkpoints, and non-goals;
- exact base, head, diff, untracked files, and unrelated changes;
- focused and complete required verification;
- documentation and plan status;
- independent correctness-review findings and their disposition;
- maintainability-review recommendations and their disposition;
- manual or native verification still required;
- branch, commit, push, and PR state;
- known limitations and explicitly deferred work;
- whether the next action remains in the current phase or warrants a fresh session;
- whether accepted decisions, checkpoint state, verification state, unresolved questions, and exact repository/Git state are durable enough for a handoff.

Classify every remaining item as blocking, recommended before merge, or deferred. The stopping condition is no unresolved blocking or important actionable findings, required verification passing, and rationale recorded for rejected or deferred findings—not an empty reviewer report.

Finish with one recommended next action. If a fresh phase session is appropriate, include the suggested `/name <task> — <phase>` command and recommend generating a self-contained `/handoff`; otherwise say explicitly that the work should continue in the current session. Do not recommend a new session for a small checkpoint in the same implementation phase.
