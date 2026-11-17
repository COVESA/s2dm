// Stages the schemas of the latest releases in `static/releases/` for the Releases page.
const { execFileSync } = require("node:child_process");
const { copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { basename, join } = require("node:path");

const SCHEMA_FILE = "schema.graphql";
const METADATA_FILE = "metadata.yaml";
const RELEASE_ARCHIVE = "release.tar.gz";
const ARCHIVE_EXTENSIONS = [".tar", ".tar.gz", ".tgz", ".zip"];
/** The release list holds at most this many releases, newest first. */
const LISTED_RELEASES_MAX = 1000;
/** The highest number of releases the script stages. */
const RELEASES_LIMIT_MAX = 50;

/** A release that cannot be staged. The code names the reason. */
class ReleaseError extends Error {
	/**
	 * @param {string} code The reason, e.g. "NO_SCHEMA_ASSET".
	 * @param {string} message The text for the build log.
	 */
	constructor(code, message) {
		super(message);
		this.code = code;
	}
}

/**
 * Reads the number of releases to stage.
 * @param {string | undefined} argument The command-line argument.
 * @returns {number | null} The limit, or null when the argument is not a whole number from 1 to `RELEASES_LIMIT_MAX`.
 */
function parseLimit(argument) {
	const limit = Number(argument);
	if (!Number.isInteger(limit) || limit < 1 || limit > RELEASES_LIMIT_MAX) {
		return null;
	}
	return limit;
}

/**
 * Tells if a file name has an archive extension.
 * @param {string} fileName The file name.
 * @returns {boolean} True for `.tar`, `.tar.gz`, `.tgz` and `.zip` files.
 */
function isArchive(fileName) {
	return ARCHIVE_EXTENSIONS.some((extension) => fileName.endsWith(extension));
}

/**
 * Picks the release asset that holds the schema.
 * A plain schema needs a metadata file next to it.
 * `release.tar.gz` comes next, then the only archive of the release.
 * @param {string[]} assetNames The names of the release assets.
 * @returns {string | null} The asset name, or null when no asset holds a schema.
 */
function pickSchemaAsset(assetNames) {
	if (assetNames.includes(SCHEMA_FILE) && assetNames.includes(METADATA_FILE)) {
		return SCHEMA_FILE;
	}
	if (assetNames.includes(RELEASE_ARCHIVE)) {
		return RELEASE_ARCHIVE;
	}
	const archives = assetNames.filter(isArchive);
	if (archives.length === 1) {
		return archives[0];
	}
	return null;
}

/**
 * Finds the schema in an extracted archive.
 * The archive needs a metadata file at the top and exactly one schema file.
 * @param {string} directory The folder that holds the extracted archive.
 * @returns {string} The path of the schema file.
 * @throws {ReleaseError} When the metadata file is missing or the schema count is not one.
 */
function findArchiveSchema(directory) {
	const metadataPath = join(directory, METADATA_FILE);
	if (!existsSync(metadataPath)) {
		throw new ReleaseError("MISSING_METADATA", `The archive has no top-level ${METADATA_FILE}.`);
	}
	const entries = readdirSync(directory, { recursive: true });
	const schemaPaths = entries.filter((entry) => basename(entry) === SCHEMA_FILE);
	if (schemaPaths.length !== 1) {
		throw new ReleaseError("SCHEMA_COUNT", `The archive has ${schemaPaths.length} ${SCHEMA_FILE} files.`);
	}
	return join(directory, schemaPaths[0]);
}

/**
 * Extracts an archive with Python, which rejects entries that point outside the target folder.
 * @param {string} archivePath The archive file.
 * @param {string} directory The target folder.
 */
function extractArchive(archivePath, directory) {
	if (archivePath.endsWith(".zip")) {
		execFileSync("python3", ["-I", "-m", "zipfile", "-e", archivePath, directory]);
		return;
	}
	execFileSync("python3", ["-I", "-m", "tarfile", "--filter", "data", "-e", archivePath, directory]);
}

/**
 * Runs the GitHub CLI.
 * @param {string[]} args The CLI arguments.
 * @returns {string} The standard output.
 */
function runGh(args) {
	return execFileSync("gh", args, { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] });
}

/**
 * Lists the tags of the published releases, newest first. Drafts and pre-releases are left out.
 * @param {(args: string[]) => string} gh Runs the GitHub CLI.
 * @returns {string[]} The release tags.
 */
function listReleaseTags(gh) {
	const listLimit = String(LISTED_RELEASES_MAX);
	const output = gh([
		"release",
		"list",
		"--exclude-drafts",
		"--exclude-pre-releases",
		"--limit",
		listLimit,
		"--json",
		"tagName",
	]);
	const releases = JSON.parse(output);
	return releases.map((release) => release.tagName);
}

/**
 * Downloads the schema of one release to `<outputDirectory>/<tag>/schema.graphql`.
 * @param {string} tag The release tag.
 * @param {string} outputDirectory The folder that holds all staged releases.
 * @param {(args: string[]) => string} gh Runs the GitHub CLI.
 * @throws {ReleaseError} When the release has no usable schema.
 */
function stageRelease(tag, outputDirectory, gh) {
	if (tag.includes("/")) {
		throw new ReleaseError("TAG_WITH_SLASH", "The tag has a '/', which a file path cannot hold.");
	}
	const output = gh(["release", "view", tag, "--json", "assets"]);
	const assetNames = JSON.parse(output).assets.map((asset) => asset.name);
	const assetName = pickSchemaAsset(assetNames);
	if (assetName === null) {
		throw new ReleaseError("NO_SCHEMA_ASSET", "No asset holds a schema.");
	}

	const temporaryRoot = tmpdir();
	const workDirectoryPrefix = join(temporaryRoot, "s2dm-release-");
	const workDirectory = mkdtempSync(workDirectoryPrefix);
	try {
		gh(["release", "download", tag, "--pattern", assetName, "--dir", workDirectory]);
		const assetPath = join(workDirectory, assetName);
		let schemaPath = assetPath;
		if (assetName !== SCHEMA_FILE) {
			const extractDirectory = join(workDirectory, "extracted");
			extractArchive(assetPath, extractDirectory);
			schemaPath = findArchiveSchema(extractDirectory);
		}
		const releaseDirectory = join(outputDirectory, tag);
		const stagedSchemaPath = join(releaseDirectory, SCHEMA_FILE);
		mkdirSync(releaseDirectory, { recursive: true });
		copyFileSync(schemaPath, stagedSchemaPath);
	} finally {
		rmSync(workDirectory, { recursive: true, force: true });
	}
}

/**
 * Stages the schemas of the latest releases and writes `releases.json` with their tags, newest first.
 * The output folder is cleared first. A release that fails is skipped and does not count toward the limit.
 * @param {object} options
 * @param {number} options.limit The number of releases to stage.
 * @param {string} options.outputDirectory The folder for the staged releases.
 * @param {(args: string[]) => string} options.gh Runs the GitHub CLI.
 * @returns {string[]} The staged tags, newest first.
 */
function stageReleases({ limit, outputDirectory, gh }) {
	rmSync(outputDirectory, { recursive: true, force: true });
	mkdirSync(outputDirectory, { recursive: true });
	const tags = listReleaseTags(gh);
	const stagedTags = [];
	for (const tag of tags) {
		if (stagedTags.length === limit) {
			break;
		}
		try {
			stageRelease(tag, outputDirectory, gh);
			stagedTags.push(tag);
		} catch (error) {
			console.warn(`Skipped release ${tag}: ${error.message}`);
		}
	}
	const releasesListPath = join(outputDirectory, "releases.json");
	const releasesList = JSON.stringify(stagedTags);
	writeFileSync(releasesListPath, releasesList);
	return stagedTags;
}

module.exports = { findArchiveSchema, parseLimit, pickSchemaAsset, ReleaseError, stageReleases };

if (require.main === module) {
	const limit = parseLimit(process.argv[2]);
	if (limit === null) {
		console.error(
			`Usage: node scripts/stage-releases.js <limit>, where <limit> is a whole number from 1 to ${RELEASES_LIMIT_MAX}.`,
		);
		process.exit(1);
	}
	const outputDirectory = join(__dirname, "..", "static", "releases");
	const stagedTags = stageReleases({ limit, outputDirectory, gh: runGh });
	console.log(`Staged ${stagedTags.length} releases in ${outputDirectory}: ${stagedTags.join(", ")}`);
}
