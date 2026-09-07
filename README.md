# Artur's Pi agent setup

Reusable configuration for the [Pi coding agent](https://github.com/earendil-works/pi-mono):

- workflow prompts for planning, implementation, review, simplification, explanation, handoff, and task completion;
- skills for isolated Git worktree setup and local Pi usage audits;
- a modal Vim editor extension;
- terminal notifications when an agent run settles;
- a Gruvbox Dark Hard theme;
- personal agent instructions and portable settings examples.

## Install as a Pi package

```sh
pi install git:github.com/ARTurleite6/pi-agent-setup
```

The package automatically exposes the extensions, skills, prompts, and theme. Pi packages execute with your user permissions, so review the source before installing or updating.

## Apply the personal configuration

The package system does not install global `AGENTS.md` or extension-specific configuration files. Copy them explicitly if wanted:

```sh
mkdir -p "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
cp personal-config/AGENTS.md "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/AGENTS.md"
cp personal-config/vim-mode.json "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/vim-mode.json"
```

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

This repository does not include credentials, authentication state, trust decisions, model caches, sessions, generated audit reports, downloaded binaries, `node_modules`, or machine-managed Herdr integration files. The machine-local `pi-linear` checkout is also excluded; install that integration separately when needed.

## License

MIT. `extensions/notify.ts` comes from Pi's MIT-licensed examples; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
