# Vim mode

A local modal editor extension for Pi.

## Modes

- Normal: enter with `Escape`
- Insert: starts here by default; re-enter with `i`, `a`, `o`, `O`
- Visual character: `v`
- Visual line: `V`
- Visual block: `Ctrl+V`
- `Escape` returns to Normal mode

The current mode is shown both on the editor border and in Pi's footer.

## Supported commands

- Motions: `h j k l`, `w b e`, `0 $`, `gg G`, `f F t T`, `; ,`
- Operators: `d c y` with motions, plus `dd cc yy`
- Editing: `x`, `r`, `p P`, `u`, `Ctrl+R`
- Search: `/`, `?`, `n`, `N`
- Visual operations: `d`, `c`, `y`
- Clipboard: yanks and deletes copy to the system clipboard; paste reads it

Control keys and unhandled non-printable keys continue through Pi's normal editor, so submission and application shortcuts remain available.

## Configuration

Edit `~/.pi/agent/vim-mode.json`, then run `/reload`:

```json
{
  "initialMode": "insert",
  "systemClipboard": true,
  "showModeInFooter": true,
  "showModeOnEditor": true
}
```
