#!/usr/bin/env python3
"""Inspect or safely create an isolated Git worktree.

Creation is dry-run by default. The script intentionally does not reuse existing
branches or destinations and never cleans, resets, commits, rebases, pushes, or
removes worktrees.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


class WorktreeError(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise WorktreeError(message)


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        fail(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def repository_info(repo: Path, base: str | None = None) -> dict[str, object]:
    requested = repo.expanduser().resolve()
    if not requested.exists():
        fail(f"repository path does not exist: {requested}")

    root = Path(git(requested, "rev-parse", "--show-toplevel")).resolve()
    common_dir_raw = git(root, "rev-parse", "--git-common-dir")
    common_dir = Path(common_dir_raw)
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()

    branch_result = git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    branch = branch_result or None
    head = git(root, "rev-parse", "HEAD")
    upstream = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False) or None
    status_lines = git(root, "status", "--porcelain=v1", "--untracked-files=normal").splitlines()

    info: dict[str, object] = {
        "repository_root": str(root),
        "git_common_dir": str(common_dir),
        "worktree": str(root),
        "branch": branch,
        "detached_head": branch is None,
        "head": head,
        "upstream": upstream,
        "dirty": bool(status_lines),
        "dirty_entries": len(status_lines),
    }

    if base:
        resolved_base = git(root, "rev-parse", "--verify", f"{base}^{{commit}}")
        merge_base = git(root, "merge-base", "HEAD", resolved_base)
        info.update(
            {
                "requested_base": base,
                "resolved_base": resolved_base,
                "merge_base": merge_base,
                "head_equals_base": head == resolved_base,
            }
        )

    return info


def branch_exists(repo: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def inspect_command(args: argparse.Namespace) -> None:
    print(json.dumps(repository_info(Path(args.repo), args.base), indent=2))


def create_command(args: argparse.Namespace) -> None:
    source_info = repository_info(Path(args.repo))
    source = Path(str(source_info["repository_root"]))
    destination = Path(args.path).expanduser().resolve()

    if args.fetch:
        if not args.apply:
            fail("--fetch requires --apply because it mutates remote-tracking refs")
        git(source, "fetch", "--prune")

    resolved_base = git(source, "rev-parse", "--verify", f"{args.base}^{{commit}}")

    if destination.exists():
        fail(f"destination already exists; inspect it explicitly instead of reusing it: {destination}")
    if branch_exists(source, args.branch):
        fail(f"local branch already exists; inspect it explicitly instead of repurposing it: {args.branch}")

    command = [
        "git",
        "-C",
        str(source),
        "worktree",
        "add",
        "-b",
        args.branch,
        str(destination),
        resolved_base,
    ]
    plan = {
        "mode": "apply" if args.apply else "dry-run",
        "source_repository": str(source),
        "git_common_dir": source_info["git_common_dir"],
        "source_branch": source_info["branch"],
        "source_head": source_info["head"],
        "source_dirty": source_info["dirty"],
        "requested_base": args.base,
        "resolved_base": resolved_base,
        "new_branch": args.branch,
        "destination": str(destination),
        "fetch": bool(args.fetch),
        "command": command,
    }
    print(json.dumps(plan, indent=2))

    if not args.apply:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, text=True)
    if result.returncode != 0:
        fail(f"git worktree add failed with exit code {result.returncode}")

    created = repository_info(destination, resolved_base)
    if created["branch"] != args.branch or created["head"] != resolved_base or created["dirty"]:
        fail("created worktree did not match the planned clean branch and base")

    print(json.dumps({"created": created}, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    inspect_parser = commands.add_parser("inspect", help="inspect repository and worktree state")
    inspect_parser.add_argument("--repo", default=".", help="path inside the checkout (default: current directory)")
    inspect_parser.add_argument("--base", help="optional base branch or commit to resolve and compare")
    inspect_parser.set_defaults(run=inspect_command)

    create_parser = commands.add_parser("create", help="plan or create a new isolated worktree")
    create_parser.add_argument("--repo", default=".", help="path inside an existing checkout")
    create_parser.add_argument("--base", required=True, help="exact base branch or commit")
    create_parser.add_argument("--branch", required=True, help="new local branch name")
    create_parser.add_argument("--path", required=True, help="new worktree destination")
    create_parser.add_argument("--fetch", action="store_true", help="run git fetch --prune before resolving the base; requires --apply")
    create_parser.add_argument("--apply", action="store_true", help="perform creation; otherwise print a dry-run plan")
    create_parser.set_defaults(run=create_command)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.run(args)
    except WorktreeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
