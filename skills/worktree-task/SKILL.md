---
name: worktree-task
description: Safely inspects or creates an isolated Git worktree for a coding task, verifying repository identity, branch, base commit, HEAD, and dirty state before edits. Use when starting work in a new branch/worktree or when concurrent agents might otherwise share a writable checkout.
---

# Worktree task

Use the bundled `scripts/worktree-task.py` for deterministic Git validation. Resolve relative paths from this skill directory.

## Safety rules

- Inspect before creating or reusing a worktree.
- Never clean, reset, stash, discard, move, or overwrite unrelated changes.
- Never share a writable worktree between concurrent agents.
- Never commit, amend, rebase, merge, push, delete a branch/worktree, or open a PR as part of setup.
- Treat a detached HEAD, unexpected repository, unexpected branch/base, existing destination, or dirty reusable worktree as a condition to report—not something to repair implicitly.
- Fetch only when the user requests or approves network mutation. `create --fetch` is explicit.
- `create` is a dry run unless `--apply` is supplied.

## Inspect the current or requested checkout

```bash
python3 scripts/worktree-task.py inspect [--repo <path>]
```

Report its repository root, common Git directory, worktree, branch, HEAD, upstream, merge base when requested, and dirty summary.

To verify an intended base:

```bash
python3 scripts/worktree-task.py inspect --repo <path> --base <branch-or-commit>
```

A base need not equal HEAD; report both the resolved base and merge base so the user can identify stacking mistakes.

## Plan worktree creation

```bash
python3 scripts/worktree-task.py create \
  --repo <existing-checkout> \
  --base <branch-or-commit> \
  --branch <new-branch> \
  --path <new-worktree-path>
```

Review the dry-run output. It must resolve the exact base commit and show the command it would execute.

## Create after explicit authorization

```bash
python3 scripts/worktree-task.py create \
  --repo <existing-checkout> \
  --base <branch-or-commit> \
  --branch <new-branch> \
  --path <new-worktree-path> \
  --apply
```

Add `--fetch` only when fetching is authorized. After creation, run `inspect` on the new path and compare its branch and HEAD with the planned values before editing files.

## Existing destination or branch

The helper deliberately refuses to repurpose an existing destination or reuse an existing branch. Inspect the existing state and ask the user to choose whether to reuse it, choose another name/path, or perform a separate explicit Git operation.

## Handoff

Always report:

- repository and common Git directory;
- source and destination worktrees;
- branch, HEAD, and resolved base;
- dirty state;
- whether fetch or creation occurred;
- any mismatch or follow-up operation requiring approval.
