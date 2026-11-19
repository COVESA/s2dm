export type LoadedRelease = {
	id: string;
	repository: string;
	tag: string;
	artifact: string;
	name: string;
	version: string;
	schemaContent: string;
	schemaId: string;
	selectionContent: string;
};

const TRAILING_SLASHES_PATTERN = /\/+$/;

/**
 * Builds the id of a loaded release. The same repository and tag give the same id.
 *
 * @param repository The repository URL. Trailing slashes are ignored.
 * @param tag The release tag.
 * @returns The id, `<repository>@<tag>`.
 */
export function getLoadedReleaseId(repository: string, tag: string): string {
	const normalizedRepository = repository.replace(TRAILING_SLASHES_PATTERN, "");
	return `${normalizedRepository}@${tag}`;
}

/**
 * Reads the owner and the repository name from a repository URL.
 *
 * @param repository The repository URL, `https://<host>/<owner>/<repository>`.
 * @returns The path `<owner>/<repository>`, without the host.
 */
export function getRepositoryPath(repository: string): string {
	const repositoryUrl = new URL(repository);
	const pathSegments = repositoryUrl.pathname
		.split("/")
		.filter((pathSegment) => pathSegment !== "");
	return pathSegments.join("/");
}

/**
 * Adds a loaded release unless one with its id exists. A stored release keeps its saved selection.
 *
 * @param loadedReleases The current loaded releases.
 * @param loadedRelease The newly loaded release.
 * @returns The loaded releases, and the stored release with that id, else `loadedRelease`.
 */
export function addLoadedRelease(
	loadedReleases: LoadedRelease[],
	loadedRelease: LoadedRelease,
): { loadedReleases: LoadedRelease[]; openedRelease: LoadedRelease } {
	const storedRelease = loadedReleases.find(
		(release) => release.id === loadedRelease.id,
	);
	if (storedRelease) {
		return { loadedReleases, openedRelease: storedRelease };
	}
	return {
		loadedReleases: [...loadedReleases, loadedRelease],
		openedRelease: loadedRelease,
	};
}

/**
 * Sets the saved selection of one loaded release.
 *
 * @param loadedReleases The current loaded releases.
 * @param releaseId The id of the release to change.
 * @param selectionContent The selection query to save.
 * @returns New loaded releases. A release with another id stays the same object.
 */
export function setLoadedReleaseSelection(
	loadedReleases: LoadedRelease[],
	releaseId: string,
	selectionContent: string,
): LoadedRelease[] {
	return loadedReleases.map((release) => {
		if (release.id !== releaseId) {
			return release;
		}
		return { ...release, selectionContent };
	});
}
