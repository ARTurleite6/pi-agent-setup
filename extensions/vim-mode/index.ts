import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { CustomEditor, type ExtensionAPI, type KeybindingsManager } from "@earendil-works/pi-coding-agent";
import { CURSOR_MARKER, Key, matchesKey, truncateToWidth, visibleWidth, type EditorTheme, type TUI } from "@earendil-works/pi-tui";

type Mode = "normal" | "insert" | "visual" | "visual-line" | "visual-block";
type Snapshot = { text: string; offset: number };
type Operator = "d" | "c" | "y";
type Pending = Operator | "g" | "f" | "F" | "t" | "T" | "r" | null;

type Config = {
	initialMode: "normal" | "insert";
	systemClipboard: boolean;
	showModeInFooter: boolean;
	showModeOnEditor: boolean;
};

const DEFAULT_CONFIG: Config = {
	initialMode: "insert",
	systemClipboard: true,
	showModeInFooter: true,
	showModeOnEditor: true,
};

function loadConfig(): Config {
	const configDir = process.env.PI_CODING_AGENT_DIR ?? join(process.env.HOME ?? "", ".pi", "agent");
	const path = join(configDir, "vim-mode.json");
	if (!existsSync(path)) return DEFAULT_CONFIG;
	try {
		return { ...DEFAULT_CONFIG, ...JSON.parse(readFileSync(path, "utf8")) };
	} catch {
		return DEFAULT_CONFIG;
	}
}

function isWord(char: string): boolean {
	return /[\p{L}\p{N}_]/u.test(char);
}

function isSpace(char: string): boolean {
	return /\s/u.test(char);
}

function clamp(value: number, min: number, max: number): number {
	return Math.max(min, Math.min(max, value));
}

function offsetAt(lines: string[], line: number, col: number): number {
	let result = 0;
	for (let i = 0; i < line; i++) result += (lines[i]?.length ?? 0) + 1;
	return result + col;
}

function pointAt(text: string, offset: number): { line: number; col: number } {
	const before = text.slice(0, clamp(offset, 0, text.length));
	const parts = before.split("\n");
	return { line: parts.length - 1, col: parts.at(-1)?.length ?? 0 };
}

function lineStart(text: string, offset: number): number {
	return text.lastIndexOf("\n", Math.max(0, offset - 1)) + 1;
}

function lineEnd(text: string, offset: number): number {
	const found = text.indexOf("\n", offset);
	return found < 0 ? text.length : found;
}

function nextWord(text: string, offset: number): number {
	let i = Math.min(text.length, offset + 1);
	while (i < text.length && isWord(text[i - 1] ?? "") === isWord(text[i] ?? "") && !isSpace(text[i] ?? "")) i++;
	while (i < text.length && !isWord(text[i] ?? "")) i++;
	return i;
}

function previousWord(text: string, offset: number): number {
	let i = Math.max(0, offset - 1);
	while (i > 0 && !isWord(text[i] ?? "")) i--;
	while (i > 0 && isWord(text[i - 1] ?? "")) i--;
	return i;
}

function wordEnd(text: string, offset: number): number {
	let i = Math.min(text.length, offset + 1);
	while (i < text.length && !isWord(text[i] ?? "")) i++;
	while (i + 1 < text.length && isWord(text[i + 1] ?? "")) i++;
	return i;
}

function writeClipboard(text: string): void {
	try {
		if (process.platform === "darwin") execFileSync("pbcopy", { input: text });
		else if (process.platform === "win32") execFileSync("clip", { input: text });
		else {
			try { execFileSync("wl-copy", { input: text }); }
			catch { execFileSync("xclip", ["-selection", "clipboard"], { input: text }); }
		}
	} catch {}
}

function readClipboard(): string | null {
	try {
		if (process.platform === "darwin") return execFileSync("pbpaste", { encoding: "utf8" });
		if (process.platform === "win32") return execFileSync("powershell", ["-NoProfile", "-Command", "Get-Clipboard -Raw"], { encoding: "utf8" });
		try { return execFileSync("wl-paste", ["--no-newline"], { encoding: "utf8" }); }
		catch { return execFileSync("xclip", ["-selection", "clipboard", "-o"], { encoding: "utf8" }); }
	} catch {
		return null;
	}
}

class VimEditor extends CustomEditor {
	private mode: Mode;
	private pending: Pending = null;
	private pendingOperator: Operator | null = null;
	private visualAnchor = 0;
	private register = "";
	private registerLinewise = false;
	private undoHistory: Snapshot[] = [];
	private redoHistory: Snapshot[] = [];
	private insertSnapshot: Snapshot | null = null;
	private search: { direction: 1 | -1; query: string } | null = null;
	private lastSearch: { direction: 1 | -1; query: string } | null = null;
	private lastFind: { direction: 1 | -1; char: string; till: boolean } | null = null;

	constructor(
		tui: TUI,
		theme: EditorTheme,
		keybindings: KeybindingsManager,
		private readonly config: Config,
		private readonly reportMode: (mode: Mode, detail?: string) => void,
	) {
		super(tui, theme, keybindings);
		this.mode = config.initialMode;
		this.report();
	}

	private get rawState(): { lines: string[]; cursorLine: number; cursorCol: number } {
		return (this as unknown as { state: { lines: string[]; cursorLine: number; cursorCol: number } }).state;
	}

	private report(detail?: string): void {
		this.reportMode(this.mode, detail ?? (this.pending ? `${this.pending}…` : undefined));
		this.tui.requestRender();
	}

	private cursorOffset(): number {
		const cursor = this.getCursor();
		return offsetAt(this.getLines(), cursor.line, cursor.col);
	}

	private snapshot(): Snapshot {
		return { text: this.getText(), offset: this.cursorOffset() };
	}

	private restore(snapshot: Snapshot): void {
		this.setTextAndCursor(snapshot.text, snapshot.offset);
	}

	private setTextAndCursor(text: string, offset: number): void {
		const normalized = text.replace(/\r\n?/g, "\n").replace(/\t/g, "    ");
		const point = pointAt(normalized, offset);
		const state = this.rawState;
		state.lines = normalized.split("\n");
		if (state.lines.length === 0) state.lines = [""];
		state.cursorLine = clamp(point.line, 0, state.lines.length - 1);
		state.cursorCol = clamp(point.col, 0, state.lines[state.cursorLine]?.length ?? 0);
		this.onChange?.(this.getText());
		this.tui.requestRender();
	}

	private pushUndo(snapshot = this.snapshot()): void {
		const last = this.undoHistory.at(-1);
		if (!last || last.text !== snapshot.text || last.offset !== snapshot.offset) this.undoHistory.push(snapshot);
		this.redoHistory = [];
	}

	private undo(): void {
		const previous = this.undoHistory.pop();
		if (!previous) return;
		this.redoHistory.push(this.snapshot());
		this.restore(previous);
	}

	private redo(): void {
		const next = this.redoHistory.pop();
		if (!next) return;
		this.undoHistory.push(this.snapshot());
		this.restore(next);
	}

	private setMode(mode: Mode): void {
		if (this.mode === "insert" && mode !== "insert") this.insertSnapshot = null;
		this.mode = mode;
		this.pending = null;
		this.pendingOperator = null;
		this.search = null;
		this.report();
	}

	private enterInsert(after = false): void {
		this.pushUndo();
		this.insertSnapshot = this.snapshot();
		if (after) this.moveHorizontal(1);
		this.setMode("insert");
	}

	private moveTo(offset: number): void {
		const point = pointAt(this.getText(), offset);
		this.rawState.cursorLine = point.line;
		this.rawState.cursorCol = point.col;
		this.tui.requestRender();
	}

	private moveHorizontal(delta: number): void {
		const text = this.getText();
		this.moveTo(clamp(this.cursorOffset() + delta, 0, text.length));
	}

	private moveVertical(delta: number): void {
		const state = this.rawState;
		const line = clamp(state.cursorLine + delta, 0, state.lines.length - 1);
		state.cursorLine = line;
		state.cursorCol = clamp(state.cursorCol, 0, state.lines[line]?.length ?? 0);
		this.tui.requestRender();
	}

	private motion(key: string): number | null {
		const text = this.getText();
		const offset = this.cursorOffset();
		const cursor = this.getCursor();
		const lines = this.getLines();
		switch (key) {
			case "h": return Math.max(lineStart(text, offset), offset - 1);
			case "l": return Math.min(lineEnd(text, offset), offset + 1);
			case "j": return offsetAt(lines, Math.min(lines.length - 1, cursor.line + 1), Math.min(cursor.col, lines[Math.min(lines.length - 1, cursor.line + 1)]?.length ?? 0));
			case "k": return offsetAt(lines, Math.max(0, cursor.line - 1), Math.min(cursor.col, lines[Math.max(0, cursor.line - 1)]?.length ?? 0));
			case "w": return nextWord(text, offset);
			case "b": return previousWord(text, offset);
			case "e": return wordEnd(text, offset);
			case "0": return lineStart(text, offset);
			case "$": return lineEnd(text, offset);
		}
		return null;
	}

	private selectedRanges(): Array<[number, number]> {
		const current = this.cursorOffset();
		if (this.mode === "visual") return [[Math.min(this.visualAnchor, current), Math.min(this.getText().length, Math.max(this.visualAnchor, current) + 1)]];
		const text = this.getText();
		if (this.mode === "visual-line") {
			const start = lineStart(text, Math.min(this.visualAnchor, current));
			const endAt = lineEnd(text, Math.max(this.visualAnchor, current));
			return [[start, endAt < text.length ? endAt + 1 : endAt]];
		}
		if (this.mode === "visual-block") {
			const a = pointAt(text, this.visualAnchor);
			const b = pointAt(text, current);
			const lines = this.getLines();
			const ranges: Array<[number, number]> = [];
			for (let line = Math.min(a.line, b.line); line <= Math.max(a.line, b.line); line++) {
				const startCol = Math.min(a.col, b.col);
				const endCol = Math.min(lines[line]?.length ?? 0, Math.max(a.col, b.col) + 1);
				if (endCol > startCol) ranges.push([offsetAt(lines, line, startCol), offsetAt(lines, line, endCol)]);
			}
			return ranges;
		}
		return [];
	}

	private yankRanges(ranges: Array<[number, number]>, linewise: boolean): void {
		const text = this.getText();
		this.register = ranges.map(([start, end]) => text.slice(start, end)).join(linewise || ranges.length > 1 ? "\n" : "");
		this.registerLinewise = linewise;
		if (this.config.systemClipboard) writeClipboard(this.register);
	}

	private applyRanges(operator: Operator, ranges: Array<[number, number]>, linewise = false): void {
		if (ranges.length === 0) return;
		this.yankRanges(ranges, linewise);
		if (operator === "y") {
			this.setMode("normal");
			return;
		}
		this.pushUndo();
		let text = this.getText();
		for (const [start, end] of [...ranges].sort((a, b) => b[0] - a[0])) text = text.slice(0, start) + text.slice(end);
		this.setTextAndCursor(text, Math.min(...ranges.map((range) => range[0])));
		if (operator === "c") {
			this.insertSnapshot = this.snapshot();
			this.setMode("insert");
		} else this.setMode("normal");
	}

	private operateMotion(operator: Operator, key: string): boolean {
		const from = this.cursorOffset();
		const to = this.motion(key);
		if (to === null) return false;
		const forward = to >= from;
		const end = forward && ["w", "e", "$", "l"].includes(key) ? Math.min(this.getText().length, to + 1) : Math.max(from, to);
		this.applyRanges(operator, [[Math.min(from, to), end]], false);
		return true;
	}

	private lineOperation(operator: Operator): void {
		const text = this.getText();
		const offset = this.cursorOffset();
		const start = lineStart(text, offset);
		const rawEnd = lineEnd(text, offset);
		const end = rawEnd < text.length ? rawEnd + 1 : rawEnd;
		this.applyRanges(operator, [[start, end]], true);
	}

	private paste(before: boolean): void {
		const clipboard = this.config.systemClipboard ? readClipboard() : null;
		const value = clipboard ?? this.register;
		if (!value) return;
		this.pushUndo();
		const text = this.getText();
		let at = this.cursorOffset();
		if (this.registerLinewise || value.includes("\n")) {
			at = before ? lineStart(text, at) : Math.min(text.length, lineEnd(text, at) + (lineEnd(text, at) < text.length ? 1 : 0));
		} else if (!before) at = Math.min(text.length, at + 1);
		this.setTextAndCursor(text.slice(0, at) + value + text.slice(at), at + Math.max(0, value.length - 1));
	}

	private openLine(above: boolean): void {
		const before = this.snapshot();
		this.pushUndo(before);
		const text = before.text;
		const start = lineStart(text, before.offset);
		const end = lineEnd(text, before.offset);
		const at = above ? start : end;
		const insertion = above ? "\n" : "\n";
		const next = text.slice(0, at) + insertion + text.slice(at);
		this.setTextAndCursor(next, above ? at : at + 1);
		this.insertSnapshot = before;
		this.setMode("insert");
	}

	private findCharacter(char: string, direction: 1 | -1, till: boolean): void {
		const text = this.getText();
		const current = this.cursorOffset();
		const start = lineStart(text, current);
		const end = lineEnd(text, current);
		const found = direction === 1 ? text.indexOf(char, current + 1) : text.lastIndexOf(char, current - 1);
		if (found < start || found > end || found < 0) return;
		this.moveTo(found - (till ? direction : 0));
		this.lastFind = { direction, char, till };
	}

	private runSearch(direction: 1 | -1, query: string): void {
		if (!query) return;
		const text = this.getText();
		const current = this.cursorOffset();
		let found = direction === 1 ? text.indexOf(query, current + 1) : text.lastIndexOf(query, current - 1);
		if (found < 0) found = direction === 1 ? text.indexOf(query) : text.lastIndexOf(query);
		if (found >= 0) this.moveTo(found);
		this.lastSearch = { direction, query };
	}

	private handleSearchInput(data: string): void {
		if (!this.search) return;
		if (matchesKey(data, Key.escape)) {
			this.search = null;
			this.report();
			return;
		}
		if (matchesKey(data, Key.enter)) {
			const search = this.search;
			this.search = null;
			this.runSearch(search.direction, search.query);
			this.report();
			return;
		}
		if (matchesKey(data, Key.backspace)) this.search.query = this.search.query.slice(0, -1);
		else if (data.length === 1 && data.charCodeAt(0) >= 32) this.search.query += data;
		this.report(`${this.search.direction === 1 ? "/" : "?"}${this.search.query}`);
	}

	override handleInput(data: string): void {
		if (this.search) {
			this.handleSearchInput(data);
			return;
		}

		if (matchesKey(data, Key.escape)) {
			if (this.mode === "insert" || this.mode.startsWith("visual")) this.setMode("normal");
			else if (this.pending) { this.pending = null; this.pendingOperator = null; this.report(); }
			else super.handleInput(data);
			return;
		}

		if (this.mode === "insert") {
			super.handleInput(data);
			return;
		}

		if (matchesKey(data, Key.ctrl("r"))) { this.redo(); return; }
		if (matchesKey(data, Key.ctrl("v"))) {
			this.visualAnchor = this.cursorOffset();
			this.setMode("visual-block");
			return;
		}

		if (this.pending) {
			const pending = this.pending;
			const prefixedOperator = this.pendingOperator;
			this.pending = null;
			this.pendingOperator = null;
			if (pending === "g" && data === "g") {
				if (prefixedOperator) {
					const end = lineEnd(this.getText(), this.cursorOffset());
					this.applyRanges(prefixedOperator, [[0, end < this.getText().length ? end + 1 : end]], true);
				} else this.moveTo(0);
			} else if (["f", "F", "t", "T"].includes(pending) && data.length === 1) {
				const from = this.cursorOffset();
				this.findCharacter(data, pending === "f" || pending === "t" ? 1 : -1, pending === "t" || pending === "T");
				if (prefixedOperator) {
					const to = this.cursorOffset();
					this.applyRanges(prefixedOperator, [[Math.min(from, to), Math.min(this.getText().length, Math.max(from, to) + 1)]]);
				}
			} else if (pending === "r" && data.length === 1) {
				const at = this.cursorOffset();
				if (at < this.getText().length && this.getText()[at] !== "\n") {
					this.pushUndo();
					const text = this.getText();
					this.setTextAndCursor(text.slice(0, at) + data + text.slice(at + 1), at);
				}
			} else if (["d", "c", "y"].includes(pending)) {
				const operator = pending as Operator;
				if (data === operator) this.lineOperation(operator);
				else if (data === "G") {
					const start = lineStart(this.getText(), this.cursorOffset());
					this.applyRanges(operator, [[start, this.getText().length]], true);
				} else if (data === "g" || ["f", "F", "t", "T"].includes(data)) {
					this.pending = data as Pending;
					this.pendingOperator = operator;
				} else this.operateMotion(operator, data);
			}
			this.report();
			return;
		}

		if (this.mode.startsWith("visual")) {
			const target = this.motion(data);
			if (target !== null) { this.moveTo(target); return; }
			if (data === "v") { this.setMode(this.mode === "visual" ? "normal" : "visual"); return; }
			if (data === "V") { this.setMode(this.mode === "visual-line" ? "normal" : "visual-line"); return; }
			if (["f", "F", "t", "T"].includes(data)) { this.pending = data as Pending; this.report(); return; }
			if (["d", "c", "y"].includes(data)) this.applyRanges(data as Operator, this.selectedRanges(), this.mode === "visual-line");
			return;
		}

		const target = this.motion(data);
		if (target !== null) { this.moveTo(target); return; }

		switch (data) {
			case "i": this.enterInsert(false); return;
			case "a": this.enterInsert(true); return;
			case "o": this.openLine(false); return;
			case "O": this.openLine(true); return;
			case "v": this.visualAnchor = this.cursorOffset(); this.setMode("visual"); return;
			case "V": this.visualAnchor = this.cursorOffset(); this.setMode("visual-line"); return;
			case "x": this.applyRanges("d", [[this.cursorOffset(), Math.min(this.getText().length, this.cursorOffset() + 1)]]); return;
			case "p": this.paste(false); return;
			case "P": this.paste(true); return;
			case "u": this.undo(); return;
			case "G": this.moveTo(this.getText().length); return;
			case "/": this.search = { direction: 1, query: "" }; this.report("/"); return;
			case "?": this.search = { direction: -1, query: "" }; this.report("?"); return;
			case "n": if (this.lastSearch) this.runSearch(this.lastSearch.direction, this.lastSearch.query); return;
			case "N": if (this.lastSearch) this.runSearch(this.lastSearch.direction === 1 ? -1 : 1, this.lastSearch.query); return;
			case ";": if (this.lastFind) this.findCharacter(this.lastFind.char, this.lastFind.direction, this.lastFind.till); return;
			case ",": if (this.lastFind) this.findCharacter(this.lastFind.char, this.lastFind.direction === 1 ? -1 : 1, this.lastFind.till); return;
			case "g": case "d": case "c": case "y": case "f": case "F": case "t": case "T": case "r":
				this.pending = data as Pending; this.report(); return;
		}

		if (data.length === 1 && data.charCodeAt(0) >= 32) return;
		super.handleInput(data);
	}

	override render(width: number): string[] {
		const rendered = super.render(width);
		const internals = this as unknown as {
			lastWidth: number;
			scrollOffset: number;
			layoutText: (width: number) => Array<{ text: string; hasCursor: boolean; cursorPos?: number }>;
		};
		const layout = internals.layoutText(internals.lastWidth);
		const maxVisible = Math.max(5, Math.floor(this.tui.terminal.rows * 0.3));
		const visible = layout.slice(internals.scrollOffset, internals.scrollOffset + maxVisible);

		if (this.mode.startsWith("visual")) {
			const logicalLines = this.getLines();
			const mapped: Array<{ start: number; end: number }> = [];
			let logicalLine = 0;
			let logicalCol = 0;
			for (const row of layout) {
				const start = offsetAt(logicalLines, logicalLine, logicalCol);
				mapped.push({ start, end: start + row.text.length });
				logicalCol += row.text.length;
				if (logicalCol >= (logicalLines[logicalLine]?.length ?? 0)) {
					logicalLine = Math.min(logicalLines.length, logicalLine + 1);
					logicalCol = 0;
				}
			}

			const ranges = this.selectedRanges();
			const paddingX = Math.min(this.getPaddingX(), Math.max(0, Math.floor((width - 1) / 2)));
			const contentWidth = Math.max(1, width - paddingX * 2);
			const leftPadding = " ".repeat(paddingX);
			const rightPadding = leftPadding;
			for (let visibleIndex = 0; visibleIndex < visible.length; visibleIndex++) {
				const row = visible[visibleIndex]!;
				const map = mapped[internals.scrollOffset + visibleIndex]!;
				let output = "";
				let sourceIndex = 0;
				for (const grapheme of row.text) {
					const absolute = map.start + sourceIndex;
					const selected = ranges.some(([start, end]) => absolute < end && absolute + grapheme.length > start);
					const cursor = row.hasCursor && row.cursorPos === sourceIndex;
					if (cursor && this.focused) output += CURSOR_MARKER;
					output += selected || cursor ? `\x1b[7m${grapheme}\x1b[0m` : grapheme;
					sourceIndex += grapheme.length;
				}
				let rowWidth = visibleWidth(row.text);
				if (row.hasCursor && row.cursorPos === row.text.length) {
					if (this.focused) output += CURSOR_MARKER;
					output += "\x1b[7m \x1b[0m";
					rowWidth++;
				}
				const fill = " ".repeat(Math.max(0, contentWidth - rowWidth));
				rendered[1 + visibleIndex] = `${leftPadding}${output}${fill}${rightPadding}`;
			}
		}

		if (!this.config.showModeOnEditor || rendered.length === 0) return rendered;
		const names: Record<Mode, string> = {
			normal: " NORMAL ", insert: " INSERT ", visual: " VISUAL ",
			"visual-line": " VISUAL LINE ", "visual-block": " VISUAL BLOCK ",
		};
		const label = names[this.mode];
		const borderIndex = Math.min(rendered.length - 1, 1 + visible.length);
		if (visibleWidth(rendered[borderIndex] ?? "") >= visibleWidth(label)) {
			rendered[borderIndex] = truncateToWidth(rendered[borderIndex] ?? "", Math.max(0, width - visibleWidth(label)), "") + label;
		}
		return rendered;
	}
}

export default function (pi: ExtensionAPI) {
	const config = loadConfig();

	pi.on("session_start", (_event, ctx) => {
		if (ctx.mode !== "tui") return;
		const reportMode = (mode: Mode, detail?: string) => {
			if (!config.showModeInFooter) return;
			const name = mode.replace("-", " ").toUpperCase();
			const text = detail ? `${name}  ${detail}` : name;
			const color = mode === "insert" ? "success" : mode.startsWith("visual") ? "warning" : "accent";
			ctx.ui.setStatus("vim-mode", ctx.ui.theme.fg(color, `-- ${text} --`));
		};
		ctx.ui.setEditorComponent((tui, theme, keybindings) => new VimEditor(tui, theme, keybindings, config, reportMode));
	});

	pi.on("session_shutdown", (_event, ctx) => {
		if (ctx.hasUI) ctx.ui.setStatus("vim-mode", undefined);
	});
}
