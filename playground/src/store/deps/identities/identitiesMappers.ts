import { nanoid } from "@reduxjs/toolkit";
import { load } from "js-yaml";
import type {
	DependenciesIdentities,
	DependencyIdentityEntry,
} from "@/api/types";
import type { DependencyIdentityDraft } from "@/types/dependencyIdentity";

export function parseDependenciesIdentitiesYaml(
	fileContent: string,
): DependenciesIdentities {
	const parsedYaml = load(fileContent);
	if (
		parsedYaml === null ||
		typeof parsedYaml !== "object" ||
		Array.isArray(parsedYaml)
	) {
		throw new Error("Dependency identities root must be a YAML object.");
	}

	const identities = parsedYaml as DependenciesIdentities;
	if (!Array.isArray(identities.identities)) {
		throw new Error(
			"Dependency identities config must contain an 'identities' array.",
		);
	}

	return identities;
}

export function parseDependencyIdentity(
	identity: DependencyIdentityEntry,
): DependencyIdentityDraft {
	return {
		id: nanoid(),
		host: identity.host,
		scope: identity.scope ?? "",
		token: identity.token,
	};
}

export function serializeDependencyIdentityDraft(
	identity: DependencyIdentityDraft,
): DependencyIdentityEntry {
	const trimmedScope = identity.scope.trim();

	return {
		host: identity.host.trim(),
		scope: trimmedScope || null,
		token: identity.token.trim(),
	};
}
