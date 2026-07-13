import { load } from "js-yaml";
import { isAbsolute } from "pathe";
import type {
	ContentInput,
	DependenciesConfig,
	DependencyConfigEntry,
	PathInput,
} from "@/api/types";
import type { DependencyDraft } from "@/types/dependency";

export function parseDependenciesConfigYaml(
	fileContent: string,
): DependenciesConfig {
	const parsedYaml = load(fileContent);
	if (
		parsedYaml === null ||
		typeof parsedYaml !== "object" ||
		Array.isArray(parsedYaml)
	) {
		throw new Error("Dependency config root must be a YAML object.");
	}

	const config = parsedYaml as DependenciesConfig;
	if (!Array.isArray(config.dependencies)) {
		throw new Error("Dependency config must contain a 'dependencies' array.");
	}

	return {
		dependencies: config.dependencies.map((dependency) => ({
			...dependency,
			selection: normalizeImportedSelection(dependency.selection),
		})),
	};
}

function normalizeImportedSelection(
	selection: DependencyConfigEntry["selection"] | string | undefined,
): ContentInput | PathInput | null {
	if (selection === undefined || selection === null) {
		return null;
	}

	if (typeof selection === "string") {
		return { type: "path", path: selection };
	}

	return selection;
}

export function hasRelativeDependencySelectionPaths(
	config: DependenciesConfig,
): boolean {
	return config.dependencies.some((dependency) => {
		if (dependency.selection?.type !== "path") {
			return false;
		}

		return !isAbsolute(dependency.selection.path);
	});
}

export function parseDependencyConfig(
	dependency: DependencyConfigEntry,
): DependencyDraft {
	let selectionType: "content" | null = null;
	let selectionContent: string | null = null;
	if (dependency.selection?.type === "content") {
		selectionType = "content";
		selectionContent = dependency.selection.content;
	}

	return {
		id: `${dependency.name}::${dependency.version}`,
		name: dependency.name,
		version: dependency.version,
		source: dependency.source,
		artifact: dependency.artifact,
		selectionType,
		selectionContent,
		schemaContent: dependency.schema_content ?? null,
	};
}

export function serializeDependencyDraft(
	dependency: DependencyDraft,
): DependencyConfigEntry {
	const trimmedSelectionContent = dependency.selectionContent?.trim() || null;
	let selection: ContentInput | null = null;
	if (dependency.selectionType === "content" && trimmedSelectionContent) {
		selection = { type: "content", content: trimmedSelectionContent };
	}

	return {
		name: dependency.name.trim(),
		version: dependency.version.trim(),
		source: dependency.source.trim(),
		artifact: dependency.artifact.trim(),
		selection,
	};
}
