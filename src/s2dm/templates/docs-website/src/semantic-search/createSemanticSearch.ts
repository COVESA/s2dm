import { fetchJson } from "@/utils/fetchJson";
import {
	decodeVectors,
	type EmbeddingsFile,
	type EmbeddingsModel,
} from "./embeddingsFile";
import type {
	EmbedQueryRequest,
	EmbedQueryResponse,
} from "./embedQuery.worker";
import { rankTable } from "./rank";

export interface SemanticSearch {
	/**
	 * Rank the elements by meaning.
	 *
	 * @param query - Free text. Blank text returns no ids.
	 * @param limit - Maximum number of ids.
	 * @returns Up to `limit` element ids, best first.
	 */
	search(query: string, limit: number): Promise<string[]>;
}

type PendingRequest = {
	resolve: (vector: Float32Array) => void;
	reject: (error: Error) => void;
};

type LoadedEmbeddings = {
	elementIds: string[];
	model: EmbeddingsModel;
	/** The decoded vectors, row-major, one row per element id. */
	table: Float32Array;
};

/**
 * Fetch an embeddings file and decode its vectors.
 *
 * Only what searching reads is returned, so the file's base64 vectors can be freed once decoded.
 *
 * @param fileUrl - URL of the `embeddings.json` written by `s2dm embeddings build`.
 * @returns The element ids, the model and the decoded vectors.
 * @throws Error when the file cannot be fetched or its vectors cannot be decoded.
 */
async function loadEmbeddings(fileUrl: string): Promise<LoadedEmbeddings> {
	const file = await fetchJson<EmbeddingsFile>(fileUrl);
	const table = decodeVectors(file);
	const elementIds = file.elements.map((element) => element.id);
	return { elementIds, model: file.model, table };
}

/**
 * Start a worker that embeds queries with the given model. The worker starts loading the model
 * at once, so the first query does not wait for the download.
 *
 * @param model - The model recorded in the embeddings file.
 * @returns A function that embeds one query into a normalized vector.
 */
function createQueryEmbedder(
	model: EmbeddingsModel,
): (query: string) => Promise<Float32Array> {
	const pendingRequests = new Map<number, PendingRequest>();
	let worker: Worker | null = null;
	let nextRequestId = 0;

	const handleResponse = (event: MessageEvent<EmbedQueryResponse>) => {
		const response = event.data;
		const pendingRequest = pendingRequests.get(response.requestId);
		pendingRequests.delete(response.requestId);
		if (!pendingRequest) {
			return;
		}
		if ("error" in response) {
			pendingRequest.reject(new Error(response.error));
			return;
		}
		pendingRequest.resolve(response.vector);
	};

	// The worker failed to load or crashed: fail every waiting query and start afresh next time.
	const handleWorkerError = (event: ErrorEvent) => {
		const workerError = new Error(event.message || "The search worker failed.");
		for (const pendingRequest of pendingRequests.values()) {
			pendingRequest.reject(workerError);
		}
		pendingRequests.clear();
		worker?.terminate();
		worker = null;
	};

	const startWorker = (): Worker => {
		// Bundlers only compile the worker when `new URL(...)` sits inline in `new Worker(...)`.
		const startedWorker = new Worker(
			new URL("./embedQuery.worker.ts", import.meta.url),
			{ type: "module" },
		);
		startedWorker.addEventListener("message", handleResponse);
		startedWorker.addEventListener("error", handleWorkerError);
		const loadRequest: EmbedQueryRequest = { type: "load", model };
		startedWorker.postMessage(loadRequest);
		return startedWorker;
	};

	worker = startWorker();

	return (query) => {
		worker ??= startWorker();
		const requestId = nextRequestId++;
		const request: EmbedQueryRequest = { type: "embed", requestId, query };
		const activeWorker = worker;
		return new Promise((resolve, reject) => {
			pendingRequests.set(requestId, { resolve, reject });
			activeWorker.postMessage(request);
		});
	};
}

/**
 * Load an embeddings file and prepare searching it by meaning.
 *
 * @param fileUrl - URL of the `embeddings.json` written by `s2dm embeddings build`.
 * @returns The search over the file's elements.
 * @throws Error when the file cannot be fetched or its vectors cannot be decoded.
 */
export async function createSemanticSearch(
	fileUrl: string,
): Promise<SemanticSearch> {
	const { elementIds, model, table } = await loadEmbeddings(fileUrl);
	const embedQuery = createQueryEmbedder(model);

	const search = async (query: string, limit: number): Promise<string[]> => {
		const trimmedQuery = query.trim();
		if (!trimmedQuery) {
			return [];
		}
		const queryVector = await embedQuery(trimmedQuery);
		const rankedIndices = rankTable(
			table,
			model.settings.dim,
			queryVector,
			limit,
		);
		return rankedIndices.map(({ index }) => elementIds[index]);
	};

	return { search };
}
