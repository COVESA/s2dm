import { expect, test } from "vitest";
import type { LoadedRelease } from "@/types/release";
import {
	formatAssetSize,
	listFallbackArchives,
	planReleaseExploration,
} from "@/utils/releaseAssets";

function buildAsset(name: string, size = 1) {
	return { name, size };
}

test("listFallbackArchives drops the direct schema and the tried asset", () => {
	const modelArchive = buildAsset("model.zip", 1536);
	const candidateAssets = [
		buildAsset("schema.graphql"),
		buildAsset("release.tar.gz"),
		modelArchive,
	];

	const archives = listFallbackArchives(candidateAssets, "release.tar.gz");

	expect(archives).toEqual([modelArchive]);
});

test("listFallbackArchives keeps every archive when none was tried", () => {
	const candidateAssets = [buildAsset("model.zip"), buildAsset("docs.tgz")];

	const archives = listFallbackArchives(candidateAssets, null);

	expect(archives).toEqual(candidateAssets);
});

test("listFallbackArchives is empty when only the tried archive exists", () => {
	const candidateAssets = [buildAsset("release.tar.gz")];

	const archives = listFallbackArchives(candidateAssets, "release.tar.gz");

	expect(archives).toEqual([]);
});

test("planReleaseExploration explores a stored release", () => {
	const storedRelease: LoadedRelease = {
		id: "https://github.com/owner/repo@v1.0.0",
		repository: "https://github.com/owner/repo",
		tag: "v1.0.0",
		artifact: "schema.graphql",
		name: "Vehicle",
		version: "v1.0.0",
		schemaContent: "type Query { ping: String }\n",
		schemaId: "opened-schema-id",
		selectionContent: "",
	};
	const candidateAssets = [buildAsset("schema.graphql")];

	const step = planReleaseExploration(storedRelease, candidateAssets);

	expect(step).toEqual({ kind: "explore", release: storedRelease });
});

test("planReleaseExploration opens the direct schema when the publish archive also exists", () => {
	const candidateAssets = [
		buildAsset("release.tar.gz"),
		buildAsset("schema.graphql"),
	];

	const step = planReleaseExploration(undefined, candidateAssets);

	expect(step).toEqual({ kind: "open", artifact: "schema.graphql" });
});

test("planReleaseExploration opens the publish archive of a new release without a direct schema", () => {
	const candidateAssets = [
		buildAsset("release.tar.gz"),
		buildAsset("model.zip"),
	];

	const step = planReleaseExploration(undefined, candidateAssets);

	expect(step).toEqual({ kind: "open", artifact: "release.tar.gz" });
});

test("planReleaseExploration lets the user choose an unknown archive", () => {
	const candidateAssets = [buildAsset("model.zip"), buildAsset("docs.tgz")];

	const step = planReleaseExploration(undefined, candidateAssets);

	expect(step).toEqual({ kind: "choose", archives: candidateAssets });
});

test("planReleaseExploration lets the user choose from no archives when a release has no assets", () => {
	const step = planReleaseExploration(undefined, []);

	expect(step).toEqual({ kind: "choose", archives: [] });
});

test("formatAssetSize shows whole bytes below one kilobyte", () => {
	const sizeText = formatAssetSize(117);

	expect(sizeText).toBe("117 B");
});

test("formatAssetSize shows kilobytes, megabytes and gigabytes with one decimal", () => {
	const kilobyteText = formatAssetSize(1536);
	const megabyteText = formatAssetSize(2242042);
	const gigabyteText = formatAssetSize(3221225472);

	expect(kilobyteText).toBe("1.5 KB");
	expect(megabyteText).toBe("2.1 MB");
	expect(gigabyteText).toBe("3.0 GB");
});
