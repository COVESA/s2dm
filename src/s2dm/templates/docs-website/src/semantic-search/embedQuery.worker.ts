import {
	AutoModel,
	AutoTokenizer,
	mean_pooling,
	type Tensor,
} from "@huggingface/transformers";
import { getErrorMessage } from "@/utils/getErrorMessage";
import type { EmbeddingsModel, ModelSource } from "./embeddingsFile";

const HUGGING_FACE_KIND = "huggingface";
const QUANTIZED_ONNX_FILE = "model_quantized.onnx";
// Matches the truncation of `s2dm embeddings build`.
const MAX_QUERY_TOKENS = 256;

type HuggingFaceSource = {
	repo: string;
	revision: string;
};

/** `load` sends the model once and starts loading it; `embed` embeds one query with it. */
export type EmbedQueryRequest =
	| { type: "load"; model: EmbeddingsModel }
	| { type: "embed"; requestId: number; query: string };

export type EmbedQueryResponse =
	| { requestId: number; vector: Float32Array }
	| { requestId: number; error: string };

type EmbedText = (text: string) => Promise<Float32Array>;

type ModelOutputs = {
	last_hidden_state: Tensor;
	sentence_embedding?: Tensor;
};

let model: EmbeddingsModel | null = null;
let embedTextPromise: Promise<EmbedText> | null = null;

/**
 * Read the Hugging Face repo and revision of a model source. The browser loads models only
 * through transformers.js, which reads from the Hugging Face Hub.
 *
 * @param source - The model source stored in the embeddings file.
 * @returns The source's repo and revision.
 * @throws Error when the source is not a Hugging Face source with a repo and a revision.
 */
function readHuggingFaceSource(source: ModelSource): HuggingFaceSource {
	const { kind, repo, revision } = source;
	if (kind !== HUGGING_FACE_KIND) {
		throw new Error(`Unsupported model source: ${kind}`);
	}
	if (typeof repo !== "string" || typeof revision !== "string") {
		throw new Error("Hugging Face model source needs a repo and a revision.");
	}
	return { repo, revision };
}

/**
 * Load the model recorded in the embeddings file, reading the vector the way the build did.
 *
 * @param embeddingsModel - The model source and settings stored in the embeddings file.
 * @returns A function that embeds one text into a normalized vector.
 * @throws Error when the model's source is not supported.
 */
async function loadEmbedText(
	embeddingsModel: EmbeddingsModel,
): Promise<EmbedText> {
	const { repo, revision } = readHuggingFaceSource(embeddingsModel.source);
	const { settings } = embeddingsModel;
	let dtype: "q8" | "fp32" = "fp32";
	const isQuantized = settings.onnx_file.endsWith(QUANTIZED_ONNX_FILE);
	if (isQuantized) {
		dtype = "q8";
	}
	const tokenizer = await AutoTokenizer.from_pretrained(repo, { revision });
	const encoder = await AutoModel.from_pretrained(repo, { revision, dtype });

	return async (text) => {
		const inputs = tokenizer([text], {
			truncation: true,
			max_length: MAX_QUERY_TOKENS,
		});
		const outputs: ModelOutputs = await encoder(inputs);
		let pooled = outputs.sentence_embedding;
		if (settings.pooling === "cls") {
			pooled = outputs.last_hidden_state.slice(null, 0);
		} else if (settings.pooling === "mean") {
			pooled = mean_pooling(outputs.last_hidden_state, inputs.attention_mask);
		}
		if (!pooled) {
			throw new Error("The model has no sentence_embedding output.");
		}
		const normalized = pooled.normalize(2, -1);
		return normalized.data as Float32Array;
	};
}

/**
 * Load the model on the first call and share the load with later calls. A failed load is dropped,
 * so the next call loads again.
 *
 * @param embeddingsModel - The model to load.
 * @returns A function that embeds one text into a normalized vector.
 */
function loadEmbedTextOnce(
	embeddingsModel: EmbeddingsModel,
): Promise<EmbedText> {
	embedTextPromise ??= loadEmbedText(embeddingsModel).catch(
		(error: unknown) => {
			embedTextPromise = null;
			throw error;
		},
	);
	return embedTextPromise;
}

/**
 * Embed one query and post the vector back, or the error.
 *
 * @param requestId - Echoed back, so the caller can match the response.
 * @param query - The query text.
 */
async function embedQuery(requestId: number, query: string): Promise<void> {
	try {
		if (!model) {
			throw new Error("The search worker received a query before its model.");
		}
		const embedText = await loadEmbedTextOnce(model);
		const vector = await embedText(`${model.settings.query_prompt}${query}`);
		const response: EmbedQueryResponse = { requestId, vector };
		const vectorBuffer = vector.buffer as ArrayBuffer;
		postMessage(response, { transfer: [vectorBuffer] });
	} catch (error) {
		const message = getErrorMessage(error);
		postMessage({ requestId, error: message } satisfies EmbedQueryResponse);
	}
}

addEventListener("message", (event: MessageEvent<EmbedQueryRequest>) => {
	const request = event.data;
	if (request.type === "load") {
		model = request.model;
		// Start loading now, so the first query does not wait for the download.
		loadEmbedTextOnce(model).catch(() => {
			// The next query loads again and reports the failure.
		});
		return;
	}
	embedQuery(request.requestId, request.query);
});
