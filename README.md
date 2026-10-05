# Artur's Pi agent setup

Reusable configuration for the [Pi coding agent](https://github.com/earendil-works/pi-mono):

- a prompt for running a task in a visible pi agent in a Herdr pane;
- skills: Matt Pocock's engineering and productivity skills (spec, tickets, TDD, code review, domain modeling, grilling, writing), and agent-stuff's `commit`, `summarize`, `tmux`, `web-browser` and `native-web-search`;
- a subagent extension: blocking single, parallel and chain dispatch, plus background runs (`subagent_start`, `subagent_wait`, `subagent_status`, `subagent_cancel`);
- agent-stuff extensions: `/goal` and goal tools, `/todos` and the `todo` tool, `/review` and `/end-review`, `/answer`;
- terminal notifications when an agent run settles;
- a Gruvbox Dark Hard theme;
- subagent definitions and a portable settings example.

## Install as a Pi package

```sh
pi install git:github.com/ARTurleite6/pi-agent-setup
```

The package automatically exposes the extensions, skills, prompts, and theme. Pi packages execute with your user permissions, so review the source before installing or updating.

The `web-browser` skill needs its script dependencies installed once:

```sh
npm ci --ignore-scripts --prefix <package-dir>/skills/web-browser/scripts
```

`/answer` and `native-web-search` use `openai-codex/gpt-6-luna`, so they need an OpenAI Codex login.

## Apply the personal configuration

The package system does not install subagent definitions. Copy them explicitly if wanted:

```sh
mkdir -p "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/agents"
cp personal-config/agents/*.md "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/agents/"
```

The subagent extension finds agents in `agents/` under the Pi agent directory, and in `.pi/agents` inside a project when the call sets `agentScope`. `personal-config/agents/` holds `worker` (all tools), `scout` (read-only investigation) and `reviewer` (read-only review). `scout` pins `claude-bridge/claude-sonnet-5-5`, which needs the `pi-claude-bridge` package; change or remove its `model:` line otherwise. The other agents use the dispatching session's model.

Background runs write a readable log per run under `$TMPDIR/pi-subagent-runs/<pid>/`. Quitting or reloading Pi stops them.

`personal-config/settings.example.json` is a portable reference. Merge the desired values into your existing `settings.json`; do not overwrite authentication or machine-local package configuration blindly.

Select the theme with `/settings` or set:

```json
{
  "theme": "gruvbox-dark-hard"
}
```

## Repository layout

```text
extensions/       Pi extensions
prompts/          Slash-command prompt templates
skills/           On-demand agent skills and helper scripts
themes/           TUI themes
personal-config/  Files that require explicit copying or merging
```

## Intentionally excluded

This repository does not include credentials, authentication state, trust decisions, model caches, sessions, generated audit reports, downloaded binaries, `node_modules`, or machine-managed Herdr integration files. The `herdr` skill that `prompts/herdr-agent.md` loads is one of those: write it with `mkdir -p ~/.pi/agent/skills/herdr && herdr --skill > ~/.pi/agent/skills/herdr/SKILL.md`. The machine-local `pi-linear` checkout is also excluded; install that integration separately when needed.

## License

MIT for this repository's own files. Third-party files keep their licenses: Pi examples (MIT), Matt Pocock's skills (MIT) and mitsuhiko/agent-stuff (Apache-2.0). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for which files come from where and what was changed, and `licenses/` for the license texts.
