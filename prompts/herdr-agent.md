---
description: Run a task in a visible pi agent in a Herdr pane
argument-hint: "<task>"
---
Run this task in a separate pi agent in a sibling Herdr pane, so I can watch it: $@

Load the `herdr` skill and follow it, with these pi specifics:

- Start it with `herdr agent start <unique-name> --kind pi --pane <id> -- --model <provider/model>`. Pass `--model` explicitly: the model I named, otherwise this session's model.
- Pi runs fullscreen, so `herdr agent read` cannot recover a long reply. In the first prompt, give the agent the full task context, have it write its report as Markdown under `$TMPDIR/pi-subagents/`, and reply only with that path. Read the file when it is done.
- If I asked for a worktree, create it with `herdr worktree create` and start the agent there.
- Do not answer the agent's approval or question prompts for me; tell me about them.
- When its result is reported or merged, close the pane and remove any worktree you created.
