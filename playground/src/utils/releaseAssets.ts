import type { ReleaseAsset } from "@/api/types";
import type { LoadedRelease } from "@/types/release";

const DIRECT_SCHEMA_ASSET = "schema.graphql";
const PUBLISH_ARCHIVE_ASSET = "release.tar.gz";

const ASSET_SIZE_UNITS = ["B", "KB", "MB", "GB"];
const ASSET_SIZE_STEP = 1024;

type ReleaseExplorationStep =
	| { kind: "explore"; release: LoadedRelease }
	| { kind: "open"; artifact: string }
	| { kind: "choose"; archives: ReleaseAsset[] };

/**
 * Chooses the asset to open first: the direct schema, else the archive of the s2dm publish action.
 *
 * @param candidateAssets The loadable assets of a release.
 * @returns The asset name, or null when no known asset exists.
 */
function pickInitialReleaseAsset(
	candidateAssets: ReleaseAsset[],
): string | null {
	const assetNames = candidateAssets.map((asset) => asset.name);
	if (assetNames.includes(DIRECT_SCHEMA_ASSET)) {
		return DIRECT_SCHEMA_ASSET;
	}

	if (assetNames.includes(PUBLISH_ARCHIVE_ASSET)) {
		return PUBLISH_ARCHIVE_ASSET;
	}

	return null;
}

/**
 * Lists the candidate archives other than the direct schema and the tried asset.
 *
 * @param candidateAssets The loadable assets of a release.
 * @param triedAsset The name of the asset that was already tried, or null.
 * @returns The candidate archives without the direct schema and without `triedAsset`.
 */
export function listFallbackArchives(
	candidateAssets: ReleaseAsset[],
	triedAsset: string | null,
): ReleaseAsset[] {
	return candidateAssets.filter(
		(asset) => asset.name !== DIRECT_SCHEMA_ASSET && asset.name !== triedAsset,
	);
}

/**
 * Decides the next step for a picked release: explore its stored release, open its initial
 * asset, or choose from its archives.
 *
 * @param storedRelease The loaded release with the picked tag, else undefined.
 * @param candidateAssets The loadable assets of the release.
 * @returns The next exploration step.
 */
export function planReleaseExploration(
	storedRelease: LoadedRelease | undefined,
	candidateAssets: ReleaseAsset[],
): ReleaseExplorationStep {
	if (storedRelease) {
		return { kind: "explore", release: storedRelease };
	}

	const initialAsset = pickInitialReleaseAsset(candidateAssets);
	if (initialAsset !== null) {
		return { kind: "open", artifact: initialAsset };
	}

	const archives = listFallbackArchives(candidateAssets, null);
	return { kind: "choose", archives };
}

/**
 * Formats an asset size for display. Each unit is 1024 times the one before.
 * Bytes are whole numbers. Larger units have one decimal.
 *
 * @param sizeInBytes The asset size in bytes.
 * @returns The size with its unit, for example "2.1 MB".
 */
export function formatAssetSize(sizeInBytes: number): string {
	if (sizeInBytes < ASSET_SIZE_STEP) {
		return `${sizeInBytes} B`;
	}

	let scaledSize = sizeInBytes;
	let unitIndex = 0;
	while (
		scaledSize >= ASSET_SIZE_STEP &&
		unitIndex < ASSET_SIZE_UNITS.length - 1
	) {
		scaledSize = scaledSize / ASSET_SIZE_STEP;
		unitIndex += 1;
	}

	const roundedSize = scaledSize.toFixed(1);
	return `${roundedSize} ${ASSET_SIZE_UNITS[unitIndex]}`;
}
