/**
 * Registry of background subagent runs.
 *
 * A run starts immediately and is tracked until its report is collected: by a
 * `subagent_wait` call that names it, or by the extension delivering it into the
 * session (see `takeUnwatchedReports`). The runner is injected so this module stays
 * independent of how the child process is spawned and parsed.
 */

export type RunState = "running" | "completed" | "failed" | "cancelled";

export interface BackgroundRun<T> {
	id: string;
	agent: string;
	task: string;
	cwd: string;
	logPath: string;
	startedAt: number;
	finishedAt?: number;
	state: RunState;
	/** Latest partial or final result reported by the runner. */
	result?: T;
	/** Set once the result has been handed to the model, by a wait or a notification. */
	collected: boolean;
	controller: AbortController;
	done: Promise<void>;
}

/** Runs the work for `run`, stopping when `run.controller.signal` aborts. */
export type Runner<T> = (run: BackgroundRun<T>, onUpdate: (partial: T) => void) => Promise<T>;

interface Waiter {
	ids: Set<string>;
	wake: () => void;
}

export class BackgroundRuns<T> {
	private readonly runs = new Map<string, BackgroundRun<T>>();
	private readonly waiters = new Set<Waiter>();
	private nextId = 1;

	constructor(
		private readonly isFailed: (result: T) => boolean,
		private readonly onUnwatchedFinish: (run: BackgroundRun<T>) => void,
	) {}

	activeCount(): number {
		let count = 0;
		for (const run of this.runs.values()) if (run.state === "running") count++;
		return count;
	}

	get(id: string): BackgroundRun<T> | undefined {
		return this.runs.get(id);
	}

	list(): BackgroundRun<T>[] {
		return [...this.runs.values()];
	}

	uncollectedIds(): string[] {
		return this.list()
			.filter((run) => !run.collected)
			.map((run) => run.id);
	}

	runningIds(): string[] {
		return this.list()
			.filter((run) => run.state === "running")
			.map((run) => run.id);
	}

	/** Finished, uncollected runs that no pending wait is watching, marked collected. */
	takeUnwatchedReports(): BackgroundRun<T>[] {
		const taken = this.list().filter(
			(run) => run.state !== "running" && !run.collected && !this.isWatched(run.id),
		);
		for (const run of taken) run.collected = true;
		return taken;
	}

	start(
		info: { agent: string; task: string; cwd: string; logPath: (id: string) => string },
		runner: Runner<T>,
	): BackgroundRun<T> {
		const id = `bg-${this.nextId++}`;
		const controller = new AbortController();
		const run: BackgroundRun<T> = {
			id,
			agent: info.agent,
			task: info.task,
			cwd: info.cwd,
			logPath: info.logPath(id),
			startedAt: Date.now(),
			state: "running",
			collected: false,
			controller,
			done: Promise.resolve(),
		};
		run.done = runner(run, (partial) => {
			run.result = partial;
		}).then(
			(result) => {
				run.result = result;
				this.finish(run, controller.signal.aborted ? "cancelled" : this.isFailed(result) ? "failed" : "completed");
			},
			() => this.finish(run, controller.signal.aborted ? "cancelled" : "failed"),
		);
		this.runs.set(id, run);
		return run;
	}

	cancel(id: string): boolean {
		const run = this.runs.get(id);
		if (!run || run.state !== "running") return false;
		// The caller asked for this, so the cancellation is not announced back to it.
		run.collected = true;
		run.controller.abort();
		return true;
	}

	cancelAll(): void {
		for (const run of this.runs.values()) this.cancel(run.id);
	}

	/**
	 * Resolves when any (or all) of `ids` has finished, when `timeoutMs` elapses, or
	 * when `signal` aborts. Runs named here are not announced by notification while
	 * the wait is pending.
	 */
	async wait(ids: string[], mode: "any" | "all", timeoutMs: number | undefined, signal: AbortSignal | undefined) {
		const runs = ids.map((id) => this.runs.get(id)).filter((run): run is BackgroundRun<T> => run !== undefined);
		const satisfied = () =>
			mode === "any" ? runs.some((run) => run.state !== "running") : runs.every((run) => run.state !== "running");
		if (runs.length === 0 || satisfied()) return;

		await new Promise<void>((resolve) => {
			let timer: ReturnType<typeof setTimeout> | undefined;
			const waiter: Waiter = {
				ids: new Set(runs.map((run) => run.id)),
				wake: () => {
					if (satisfied()) settle();
				},
			};
			const settle = () => {
				this.waiters.delete(waiter);
				if (timer) clearTimeout(timer);
				signal?.removeEventListener("abort", settle);
				resolve();
			};
			this.waiters.add(waiter);
			if (timeoutMs !== undefined) timer = setTimeout(settle, timeoutMs);
			if (signal?.aborted) settle();
			else signal?.addEventListener("abort", settle, { once: true });
		});
	}

	private isWatched(id: string): boolean {
		return [...this.waiters].some((waiter) => waiter.ids.has(id));
	}

	private finish(run: BackgroundRun<T>, state: RunState): void {
		run.state = state;
		run.finishedAt = Date.now();
		const watched = this.isWatched(run.id);
		for (const waiter of [...this.waiters]) waiter.wake();
		if (!watched && !run.collected) this.onUnwatchedFinish(run);
	}
}
