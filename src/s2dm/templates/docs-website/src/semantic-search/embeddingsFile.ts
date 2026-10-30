const FORMAT_VERSION = 1;

const FLOAT16_BYTES = 2;

const LITTLE_ENDIAN = true;

type Pooling = "sentence_embedding" | "cls" | "mean";

/** Where the model comes from. `kind` names the source; the other fields belong to that source. */
export type ModelSource = {
	kind: string;
	[field: string]: unknown;
};

type ModelSettings = {
	onnx_file: string;
	pooling: Pooling;
	query_prompt: string;
	dim: number;
};

export type EmbeddingsModel = {
	source: ModelSource;
	settings: ModelSettings;
};

/** The parts of `embeddings.json`, as written by `s2dm embeddings build`, that the site reads. */
export type EmbeddingsFile = {
	format_version: number;
	model: EmbeddingsModel;
	elements: { id: string }[];
	/** Base64 of little-endian float16 values, row-major, one row per element. */
	vectors: string;
};

/**
 * Decode the stored vector table of an embeddings file.
 *
 * @param file - The embeddings file.
 * @returns The vectors as one row-major `Float32Array` of `elements.length × model.settings.dim` values.
 * @throws Error when the format version is unsupported or the stored vectors do not match the
 *   number of elements and the model's vector size.
 */
export function decodeVectors(file: EmbeddingsFile): Float32Array {
	if (file.format_version !== FORMAT_VERSION) {
		throw new Error(
			`Unsupported embeddings format version ${file.format_version}; expected ${FORMAT_VERSION}.`,
		);
	}
	const binary = atob(file.vectors);
	const valueCount = file.elements.length * file.model.settings.dim;
	const expectedByteCount = valueCount * FLOAT16_BYTES;
	if (binary.length !== expectedByteCount) {
		throw new Error(
			`Stored vectors hold ${binary.length} bytes; expected ${expectedByteCount}.`,
		);
	}
	const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
	const view = new DataView(bytes.buffer);
	const table = new Float32Array(valueCount);
	for (let index = 0; index < valueCount; index++) {
		const byteOffset = index * FLOAT16_BYTES;
		table[index] = view.getFloat16(byteOffset, LITTLE_ENDIAN);
	}
	return table;
}
