import type {
	LedgerOperation,
	LedgerOperations,
	LedgerRequest,
	LedgerResponse,
} from "@ledger-ui/data/ledgerWorker";
import type { LedgerTable } from "@ledger-ui/data/types";

type Payload<K extends LedgerOperation> = Parameters<LedgerOperations[K]>;
type Result<K extends LedgerOperation> = Awaited<
	ReturnType<LedgerOperations[K]>
>;

export class LedgerWorkCancelled extends Error {
	constructor(message: string) {
		super(message);
		this.name = "LedgerWorkCancelled";
	}
}

type PendingRequest = {
	operation: LedgerOperation;
	payload: unknown;
	resolve: (value: unknown) => void;
	reject: (reason: Error) => void;
};

type WorkerSession = {
	post: <K extends LedgerOperation>(
		operation: K,
		...payload: Payload<K>
	) => Promise<Result<K>>;
	stop: (reason: Error) => void;
	/** Ends the worker, failing one operation and handing back the rest. */
	interrupt: (aborted: LedgerOperation, reason: Error) => PendingRequest[];
	resume: (requests: PendingRequest[]) => void;
};

let session: WorkerSession | null = null;
// The session an open is being attempted on. It replaces the one above only
// once it has a database, so a file that fails to open changes nothing.
let candidate: WorkerSession | null = null;
let opened: Promise<LedgerTable[]> | null = null;
let wasmUrl: string | null = null;
// Kept because terminating the worker is the only way to stop SQLite mid
// statement, and the ledger has to be reopened from something afterwards.
let ledgerBytes: Uint8Array | null = null;
let nextRequestId = 1;

// Host-provided because each bundler names the wasm asset its own way.
export function configureLedgerWorker(options: { wasmUrl: string }): void {
	wasmUrl = options.wasmUrl;
}

function startWorker(): WorkerSession {
	// A plain relative specifier: what both bundlers recognise as a worker entry.
	const worker = new Worker(new URL("./ledgerWorker.ts", import.meta.url), {
		type: "module",
	});
	const pending = new Map<number, PendingRequest>();

	const take = (): PendingRequest[] => {
		const waiting = [...pending.values()];
		pending.clear();
		return waiting;
	};

	const register = (request: PendingRequest) => {
		const id = nextRequestId;
		nextRequestId += 1;
		pending.set(id, request);
		worker.postMessage({
			id,
			operation: request.operation,
			payload: request.payload,
		} satisfies LedgerRequest);
	};

	worker.onmessage = (event: MessageEvent<LedgerResponse>) => {
		const response = event.data;
		const waiting = pending.get(response.id);
		if (!waiting) {
			return;
		}
		pending.delete(response.id);
		if (response.ok) {
			waiting.resolve(response.value);
			return;
		}
		const failure = new Error(response.message);
		failure.name = response.name;
		waiting.reject(failure);
	};

	// A worker that never started answers nothing, so nothing would settle these.
	worker.onerror = (event: ErrorEvent) => {
		const failure = new Error(event.message || "The ledger worker failed.");
		for (const request of take()) {
			request.reject(failure);
		}
	};

	return {
		post: (operation, ...payload) =>
			new Promise((resolve, reject) => {
				register({
					operation,
					payload: payload[0],
					resolve: resolve as (value: unknown) => void,
					reject,
				});
			}),
		stop: (reason) => {
			worker.terminate();
			for (const request of take()) {
				request.reject(reason);
			}
		},
		interrupt: (aborted, reason) => {
			worker.terminate();
			const carried: PendingRequest[] = [];
			for (const request of take()) {
				if (request.operation === aborted) {
					request.reject(reason);
				} else {
					carried.push(request);
				}
			}
			return carried;
		},
		resume: (requests) => {
			for (const request of requests) {
				register(request);
			}
		},
	};
}

// Answers with the schema. The ledger already loaded stays until this one reads.
export async function openLedgerInWorker(
	bytes: Uint8Array,
): Promise<LedgerTable[]> {
	if (!wasmUrl) {
		throw new Error(
			"configureLedgerWorker has not been called with a wasm URL.",
		);
	}

	candidate?.stop(new LedgerWorkCancelled("Superseded by a newer ledger."));
	const opening = startWorker();
	candidate = opening;
	// The worker gets its own copy, leaving these bytes to reopen from later.
	const reading = opening.post("open", { bytes: bytes.slice(), wasmUrl });

	let tables: LedgerTable[];
	try {
		tables = await reading;
	} catch (error) {
		opening.stop(new LedgerWorkCancelled("The ledger could not be opened."));
		if (candidate === opening) {
			candidate = null;
		}
		throw error;
	}

	session?.stop(new LedgerWorkCancelled("Replaced by a newer ledger."));
	session = opening;
	candidate = null;
	opened = reading;
	ledgerBytes = bytes;
	return tables;
}

// Waits for the open first, so a request made during a restart reaches it.
export async function callLedger<K extends LedgerOperation>(
	operation: K,
	...payload: Payload<K>
): Promise<Result<K>> {
	if (!session || !opened) {
		throw new Error("No ledger database is loaded.");
	}
	const current = session;
	await opened;
	if (session !== current) {
		throw new LedgerWorkCancelled("The ledger was replaced.");
	}
	return current.post(operation, ...payload);
}

// Fails the running query and reopens the ledger behind it: SQLite can only be
// stopped with its thread. Other work is carried over rather than failed.
export function cancelLedgerWork(reason: string): void {
	if (!session) {
		return;
	}
	const carried = session.interrupt(
		"runQuery",
		new LedgerWorkCancelled(reason),
	);
	if (!ledgerBytes || !wasmUrl) {
		session = null;
		opened = null;
		for (const request of carried) {
			request.reject(new LedgerWorkCancelled("The ledger was closed."));
		}
		return;
	}

	const restarted = startWorker();
	session = restarted;
	opened = restarted.post("open", { bytes: ledgerBytes.slice(), wasmUrl });
	// After the reopen: the worker takes messages in order, but open awaits wasm.
	opened.then(
		() => restarted.resume(carried),
		() => {
			for (const request of carried) {
				request.reject(
					new LedgerWorkCancelled("The ledger could not be reopened."),
				);
			}
		},
	);
}

export function closeLedgerWorker(): void {
	const reason = new LedgerWorkCancelled("The ledger was closed.");
	candidate?.stop(reason);
	session?.stop(reason);
	candidate = null;
	session = null;
	opened = null;
	ledgerBytes = null;
}
