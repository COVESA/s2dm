import { describe, expect, it } from "vitest";
import {
	type FileRemoval,
	getFileRemovalPrompt,
} from "@/utils/fileRemovalPrompt";

const NO_COMPOSED_ITEMS = {
	hasSchema: false,
	hasSelection: false,
	hasExportResults: false,
};

function createRemoval(overrides: Partial<FileRemoval>): FileRemoval {
	return {
		fileName: "vehicle.graphql",
		isLastFile: false,
		isComposed: false,
		isLastComposedFile: false,
		composedItems: NO_COMPOSED_ITEMS,
		...overrides,
	};
}

describe("getFileRemovalPrompt", () => {
	it("prompts for the last file when a composed item exists", () => {
		const removal = createRemoval({
			isLastFile: true,
			composedItems: { ...NO_COMPOSED_ITEMS, hasSchema: true },
		});

		const prompt = getFileRemovalPrompt(removal);

		expect(prompt.isDataLost).toBe(true);
	});

	it("does not prompt for the last file when no composed item exists", () => {
		const removal = createRemoval({ isLastFile: true });

		const prompt = getFileRemovalPrompt(removal);

		expect(prompt.isDataLost).toBe(false);
	});

	it("prompts for the last composed file when a composed item exists", () => {
		const removal = createRemoval({
			isComposed: true,
			isLastComposedFile: true,
			composedItems: { ...NO_COMPOSED_ITEMS, hasExportResults: true },
		});

		const prompt = getFileRemovalPrompt(removal);

		expect(prompt.isDataLost).toBe(true);
	});

	it("does not prompt for the last composed file when no composed item exists", () => {
		const removal = createRemoval({
			isComposed: true,
			isLastComposedFile: true,
		});

		const prompt = getFileRemovalPrompt(removal);

		expect(prompt.isDataLost).toBe(false);
	});

	it("prompts for a composed file when a selection exists", () => {
		const removal = createRemoval({
			isComposed: true,
			composedItems: { ...NO_COMPOSED_ITEMS, hasSelection: true },
		});

		const prompt = getFileRemovalPrompt(removal);

		expect(prompt.isDataLost).toBe(true);
	});

	it("does not prompt for a composed file without a selection", () => {
		const removal = createRemoval({
			isComposed: true,
			composedItems: { ...NO_COMPOSED_ITEMS, hasSchema: true },
		});

		const prompt = getFileRemovalPrompt(removal);

		expect(prompt.isDataLost).toBe(false);
	});

	it("does not prompt for a file added after the compose", () => {
		const removal = createRemoval({
			composedItems: {
				hasSchema: true,
				hasSelection: true,
				hasExportResults: true,
			},
		});

		const prompt = getFileRemovalPrompt(removal);

		expect(prompt.isDataLost).toBe(false);
	});
});
