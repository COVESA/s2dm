import { readFile } from "node:fs/promises";
import { expect, test } from "vitest";

const ESM_ORIGIN = "https://esm.sh";
/**
 * The prefix of esm.sh's shims for Node built-in modules. The shims belong to
 * no npm package, so their URLs name no version.
 */
const NODE_SHIM_URL_PREFIX = `${ESM_ORIGIN}/node/`;
const WORKER_SETUP_SOURCE_URL = new URL(
	"../src/language-support/monacoWorkers.ts",
	import.meta.url,
);
const PACKAGE_MANIFEST_URL = new URL("../package.json", import.meta.url);

const WORKER_URL_PATTERN = /https:\/\/esm\.sh\/[^"'\s]+\?worker[^"'\s]*/g;
const MODULE_REFERENCE_PATTERN =
	/(?:from|import)\s*"(\/[^"]+)"|"(https:\/\/esm\.sh\/[^"]+)"/g;
const MONACO_EDITOR_VERSION_PATTERN = /monaco-editor@([^/,&?\s]+)/g;
const PACKAGE_VERSION_PATTERN =
	/^https:\/\/esm\.sh\/(?:@[^/]+\/)?[^/@]+@([^/?]+)/;
const EXACT_VERSION_PATTERN = /^\d+\.\d+\.\d+(?:-[\w.]+)?$/;
/**
 * The time in milliseconds that the crawl of the worker modules may take. The
 * crawl requests every module from esm.sh over the network.
 */
const MODULE_CRAWL_TIMEOUT_MS = 10_000;

type PackageManifest = {
	dependencies: Record<string, string>;
};

const workerSetupSource = await readFile(WORKER_SETUP_SOURCE_URL, "utf8");
const workerUrls = workerSetupSource.match(WORKER_URL_PATTERN) ?? [];

/**
 * Lists the esm.sh modules that a module's source code refers to, both as
 * root-relative imports and as absolute URLs.
 *
 * @param source The module's source code.
 * @returns The absolute URLs of the referenced modules.
 */
function listReferencedUrls(source: string): string[] {
	const references = source.matchAll(MODULE_REFERENCE_PATTERN);
	return [...references].map(
		([, relativePath, absoluteUrl]) =>
			absoluteUrl ?? `${ESM_ORIGIN}${relativePath}`,
	);
}

/**
 * Requests modules from esm.sh, starting at the given URLs and following
 * every module they refer to. Each URL is requested once.
 *
 * @param startUrls The URLs to start from.
 * @returns The HTTP status of every requested module, by URL.
 */
async function crawlModules(startUrls: string[]): Promise<Map<string, number>> {
	const statusByUrl = new Map<string, number>();
	const pendingUrls = [...startUrls];
	while (pendingUrls.length > 0) {
		const url = pendingUrls.pop();
		if (url === undefined || statusByUrl.has(url)) {
			continue;
		}

		const response = await fetch(url);
		statusByUrl.set(url, response.status);
		if (!response.ok) {
			continue;
		}

		const source = await response.text();
		const referencedUrls = listReferencedUrls(source);
		pendingUrls.push(...referencedUrls);
	}

	return statusByUrl;
}

/**
 * Tells whether a module URL names an exact package version.
 *
 * @param url The module URL.
 * @returns Whether the package version is exact, for example `1.9.0` and not
 * `^1.9.0`; `false` when the URL names no version.
 */
function hasExactVersion(url: string): boolean {
	const versionMatch = PACKAGE_VERSION_PATTERN.exec(url);
	if (!versionMatch) {
		return false;
	}

	return EXACT_VERSION_PATTERN.test(versionMatch[1]);
}

test("the worker setup imports the Monaco workers from esm.sh", () => {
	expect(workerUrls).not.toHaveLength(0);
});

test("the worker URLs use the monaco-editor version of package.json", async () => {
	const manifestText = await readFile(PACKAGE_MANIFEST_URL, "utf8");
	const manifest: PackageManifest = JSON.parse(manifestText);
	const expectedVersion = manifest.dependencies["monaco-editor"];
	const workerUrlText = workerUrls.join("\n");
	const versionMatches = workerUrlText.matchAll(MONACO_EDITOR_VERSION_PATTERN);
	const versions = [...versionMatches].map(([, version]) => version);
	const uniqueVersions = new Set(versions);

	expect([...uniqueVersions]).toEqual([expectedVersion]);
});

test(
	"every worker module loads from esm.sh with an exact version",
	{ timeout: MODULE_CRAWL_TIMEOUT_MS },
	async () => {
		const statusByUrl = await crawlModules(workerUrls);
		const failedUrls = [...statusByUrl]
			.filter(([, status]) => status !== 200)
			.map(([url]) => url);
		const crawledUrls = [...statusByUrl.keys()];
		const packageUrls = crawledUrls.filter(
			(url) => !url.startsWith(NODE_SHIM_URL_PREFIX),
		);
		const unpinnedUrls = packageUrls.filter((url) => !hasExactVersion(url));

		expect({ failedUrls, unpinnedUrls }).toEqual({
			failedUrls: [],
			unpinnedUrls: [],
		});
	},
);
