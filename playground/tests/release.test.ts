import { expect, test } from "vitest";
import {
	addLoadedRelease,
	getLoadedReleaseId,
	getRepositoryPath,
	type LoadedRelease,
	setLoadedReleaseSelection,
} from "@/types/release";

const STORED_RELEASE: LoadedRelease = {
	id: "https://github.com/owner/repo@v1.0.0",
	repository: "https://github.com/owner/repo",
	tag: "v1.0.0",
	artifact: "release.tar.gz",
	name: "Vehicle",
	version: "v1.0.0",
	schemaContent: "type Query { ping: String }\n",
	schemaId: "stored-schema-id",
	selectionContent: "query { ping }",
};

const OTHER_RELEASE: LoadedRelease = {
	...STORED_RELEASE,
	id: "https://github.com/owner/repo@v2.0.0",
	tag: "v2.0.0",
	version: "v2.0.0",
	selectionContent: "",
};

test("addLoadedRelease adds a release with a new id and opens it", () => {
	const result = addLoadedRelease([STORED_RELEASE], OTHER_RELEASE);

	expect(result.loadedReleases).toEqual([STORED_RELEASE, OTHER_RELEASE]);
	expect(result.openedRelease).toBe(OTHER_RELEASE);
});

test("addLoadedRelease keeps the stored release for a known id and opens it", () => {
	const reloadedRelease: LoadedRelease = {
		...STORED_RELEASE,
		selectionContent: "",
	};

	const result = addLoadedRelease([STORED_RELEASE], reloadedRelease);

	expect(result.loadedReleases).toEqual([STORED_RELEASE]);
	expect(result.openedRelease.selectionContent).toBe("query { ping }");
});

test("setLoadedReleaseSelection changes only the release with the id", () => {
	const loadedReleases = setLoadedReleaseSelection(
		[STORED_RELEASE, OTHER_RELEASE],
		OTHER_RELEASE.id,
		"query { pong }",
	);

	expect(loadedReleases[0].selectionContent).toBe("query { ping }");
	expect(loadedReleases[1].selectionContent).toBe("query { pong }");
});

test("setLoadedReleaseSelection leaves the loaded releases unchanged for an unknown id", () => {
	const loadedReleases = setLoadedReleaseSelection(
		[STORED_RELEASE],
		"unknown",
		"query { x }",
	);

	expect(loadedReleases).toEqual([STORED_RELEASE]);
});

test("getLoadedReleaseId joins the repository and the tag", () => {
	const loadedReleaseId = getLoadedReleaseId(
		"https://github.com/owner/repo",
		"v1.0.0",
	);

	expect(loadedReleaseId).toBe("https://github.com/owner/repo@v1.0.0");
});

test("getLoadedReleaseId ignores trailing slashes of the repository", () => {
	const loadedReleaseId = getLoadedReleaseId(
		"https://github.com/owner/repo//",
		"v1.0.0",
	);

	expect(loadedReleaseId).toBe("https://github.com/owner/repo@v1.0.0");
});

test("getRepositoryPath reads the owner and the repository of a GitHub URL", () => {
	const repositoryPath = getRepositoryPath("https://github.com/owner/repo");

	expect(repositoryPath).toBe("owner/repo");
});

test("getRepositoryPath ignores a trailing slash", () => {
	const repositoryPath = getRepositoryPath("https://github.com/owner/repo/");

	expect(repositoryPath).toBe("owner/repo");
});

test("getRepositoryPath leaves out a GitHub Enterprise host", () => {
	const repositoryPath = getRepositoryPath(
		"https://git.example.com/team/models",
	);

	expect(repositoryPath).toBe("team/models");
});
