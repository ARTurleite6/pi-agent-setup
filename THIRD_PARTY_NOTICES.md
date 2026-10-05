# Third-party notices

## Pi examples

MIT License, Copyright (c) 2025 Mario Zechner (full text below).

- `extensions/notify.ts` is copied from the Pi coding-agent examples:
  <https://github.com/earendil-works/pi-mono/blob/main/packages/coding-agent/examples/extensions/notify.ts>
  Local change: it skips the notification outside the TUI, where the escape sequence would corrupt print/JSON output.
- `extensions/subagent/` is adapted from the Pi 1.0.2 subagent example:
  <https://github.com/earendil-works/pi-mono/tree/main/packages/coding-agent/examples/extensions/subagent>
  The header of `extensions/subagent/index.ts` lists the local changes.

```text
MIT License

Copyright (c) 2025 Mario Zechner

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## mitsuhiko/agent-stuff

Apache License 2.0, Copyright Armin Ronacher. Source: <https://github.com/mitsuhiko/agent-stuff> at commit `0865c849befd2021490679f96a8dee58c84ac857`. License text: [`licenses/agent-stuff-LICENSE`](licenses/agent-stuff-LICENSE).

Unchanged:

- `extensions/goal.ts`, `extensions/todos.ts`, `extensions/review.ts`
- `skills/commit/`, `skills/summarize/`, `skills/tmux/`
- `skills/web-browser/`, except `scripts/package-lock.json`, regenerated with `npm audit fix --ignore-scripts` to move `ws` to a patched version inside the upstream `package.json` range

Modified:

- `extensions/answer.ts`: question extraction uses only `openai-codex/gpt-6-luna` and fails with a notification when it is not configured, instead of falling back through other Codex models, Haiku and the current model; the non-interactive guard checks `ctx.mode !== "tui"` instead of `!ctx.hasUI`.
- `skills/native-web-search/search.mjs`: the OpenAI Codex search model is `gpt-6-luna` instead of `gpt-5.4-mini`.

## Matt Pocock's skills

MIT License, Copyright (c) 2026 Matt Pocock. Source: <https://github.com/mattpocock/skills> at commit `4588b32ecab9ecc9fc8cc6b6c5e7d675b6004b0d`. License text: [`licenses/mattpocock-skills-LICENSE`](licenses/mattpocock-skills-LICENSE).

Copied: `ask-matt`, `claude-handoff`, `code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `git-guardrails-claude-code`, `grill-me`, `grill-with-docs`, `grilling`, `handoff`, `implement`, `implement-spec`, `improve-codebase-architecture`, `loop-me`, `migrate-to-shoehorn`, `pr`, `prototype`, `research`, `retro`, `scaffold-exercises`, `setup-matt-pocock-skills`, `setup-pre-commit`, `setup-ts-deep-modules`, `tdd`, `teach`, `to-questionnaire`, `to-spec`, `to-tickets`, `triage`, `wait-what`, `wayfinder`, `wizard`, `writing-beats`, `writing-fragments`, `writing-for-agents`, `writing-shape`.

All are unchanged from upstream, except that `pr/SKILL.md` drops a trailing blank line. `pr/CREDITS.md` is upstream's attribution for content taken from Dex Horthy's `show-me` skill (HumanLayer).
