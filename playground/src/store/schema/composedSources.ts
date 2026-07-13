import { createSelector } from "@reduxjs/toolkit";
import {
	selectComposedDependenciesSchema,
	selectHasComposedDependenciesSchema,
} from "@/store/deps/compose/composeSlice";
import {
	selectIncludeBuiltDependencies,
	selectSourceFiles,
} from "@/store/schema/schemaSlice";
import type { SchemaSource } from "@/types/schemaSource";

export const selectComposedSources = createSelector(
	[
		selectSourceFiles,
		selectIncludeBuiltDependencies,
		selectHasComposedDependenciesSchema,
		selectComposedDependenciesSchema,
	],
	(
		sourceFiles,
		includeBuiltDependencies,
		hasComposedDependenciesSchema,
		composedDependenciesSchema,
	): SchemaSource[] => {
		if (
			includeBuiltDependencies &&
			hasComposedDependenciesSchema &&
			composedDependenciesSchema
		) {
			return [
				...sourceFiles,
				{ type: "content", content: composedDependenciesSchema },
			];
		}
		return sourceFiles;
	},
);
