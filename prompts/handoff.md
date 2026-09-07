---
description: Produce a self-contained prompt for the next Pi session
argument-hint: "[next task or slice]"
---
Produce a self-contained prompt for the next Pi session.

Next task: ${@:-infer the next accepted step}

Include:

- current phase and destination phase;
- a suggested destination session name in the form `<task> — <phase>` and the exact `/name <task> — <phase>` command for the user;
- why a fresh session is preferable to continuing, or why continuing remains appropriate;
- repository and intended worktree;
- exact branch, HEAD, and required base branch or commit;
- current implementation and plan status;
- accepted decisions and unresolved questions;
- relevant instructions, plans, ADRs, documentation, source files, and tests;
- exact scope and explicit non-goals;
- closest code expected to be reused or extended;
- verification completed and still required;
- known failures and whether they are related;
- shared VM, host, port, fixture, or environment constraints;
- Git, commit, push, and PR policy;
- applicable independent correctness and maintainability review gates.

Before producing the prompt, verify that accepted decisions, checkpoint state, verification state, unresolved questions, and exact repository/Git state are present in the durable plan or handoff context. Do not create a new session merely for a small checkpoint within the same implementation phase.

Do not perform the next task or claim to execute `/name`. Output only the copyable prompt in one fenced Markdown block, with no introduction or trailing commentary.
