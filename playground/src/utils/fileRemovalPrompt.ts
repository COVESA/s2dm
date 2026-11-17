type ComposedItems = {
	hasSchema: boolean;
	hasSelection: boolean;
	hasExportResults: boolean;
};

export type FileRemoval = {
	fileName: string;
	isLastFile: boolean;
	isComposed: boolean;
	isLastComposedFile: boolean;
	composedItems: ComposedItems;
};

type FileRemovalPrompt = {
	isDataLost: boolean;
	description: string;
};

const ITEM_LIST_FORMAT = new Intl.ListFormat("en", { type: "conjunction" });

/**
 * Names the composed items that exist, as one list.
 *
 * @param composedItems Which composed items exist.
 * @returns The list, such as "the composed schema and the selection query".
 */
function formatComposedItems(composedItems: ComposedItems): string {
	const itemNames: string[] = [];
	if (composedItems.hasSchema) {
		itemNames.push("the composed schema");
	}
	if (composedItems.hasSelection) {
		itemNames.push("the selection query");
	}
	if (composedItems.hasExportResults) {
		itemNames.push("the export results");
	}

	return ITEM_LIST_FORMAT.format(itemNames);
}

/**
 * Tells whether the removal of one file loses data, and which data.
 *
 * @param removal The removed file and the state of the composition.
 * @returns Whether data is lost, and the sentence that names the loss.
 */
export function getFileRemovalPrompt(removal: FileRemoval): FileRemovalPrompt {
	const { fileName, composedItems } = removal;
	const hasComposedItems =
		composedItems.hasSchema ||
		composedItems.hasSelection ||
		composedItems.hasExportResults;
	const composedItemList = formatComposedItems(composedItems);

	if (removal.isLastFile) {
		return {
			isDataLost: hasComposedItems,
			description: `Removing ${fileName} clears ${composedItemList}.`,
		};
	}
	if (removal.isLastComposedFile) {
		return {
			isDataLost: hasComposedItems,
			description: `${fileName} is the last file of the composed schema. The remaining files no longer match ${composedItemList}.`,
		};
	}
	if (removal.isComposed) {
		return {
			isDataLost: composedItems.hasSelection,
			description: `${fileName} is part of the composed schema. The selection query may no longer fit after the next compose.`,
		};
	}

	return { isDataLost: false, description: "" };
}
