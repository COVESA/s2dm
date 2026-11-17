const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { dirname, join } = require("node:path");
const { test } = require("node:test");
const { findArchiveSchema, parseLimit, pickSchemaAsset, stageReleases } = require("./stage-releases.js");

/** Creates a temporary folder that is removed after the test. */
function createTemporaryDirectory(context) {
  const temporaryRoot = tmpdir();
  const directoryPrefix = join(temporaryRoot, "stage-releases-test-");
  const directory = mkdtempSync(directoryPrefix);
  context.after(() => rmSync(directory, { recursive: true, force: true }));
  return directory;
}

/** Writes files, keyed by relative path, into a folder. */
function writeFiles(directory, files) {
  for (const [relativePath, content] of Object.entries(files)) {
    const filePath = join(directory, relativePath);
    const parentDirectory = dirname(filePath);
    mkdirSync(parentDirectory, { recursive: true });
    writeFileSync(filePath, content);
  }
}

/** Builds a `.tar.gz` archive of the given files and returns its bytes. */
function createTarGz(context, files) {
  const directory = createTemporaryDirectory(context);
  const sourceDirectory = join(directory, "source");
  writeFiles(sourceDirectory, files);
  const archivePath = join(directory, "archive.tar.gz");
  execFileSync("tar", ["-czf", archivePath, "-C", sourceDirectory, "."]);
  return readFileSync(archivePath);
}

/**
 * Fakes the GitHub CLI for a list of releases, newest first.
 * Each release has a tag, its assets keyed by name, and an optional `failDownload` flag.
 */
function createFakeGh(releases) {
  const calls = [];
  const gh = (args) => {
    calls.push(args);
    const [, command, tag] = args;
    if (command === "list") {
      const listedReleases = releases.map((release) => ({ tagName: release.tag }));
      return JSON.stringify(listedReleases);
    }
    const release = releases.find((candidate) => candidate.tag === tag);
    if (command === "view") {
      const assets = Object.keys(release.assets).map((name) => ({ name }));
      return JSON.stringify({ assets });
    }
    if (release.failDownload) {
      throw new Error("download failed");
    }
    const assetName = args[args.indexOf("--pattern") + 1];
    const directory = args[args.indexOf("--dir") + 1];
    const assetPath = join(directory, assetName);
    writeFileSync(assetPath, release.assets[assetName]);
    return "";
  };
  return { gh, calls };
}

/** Stages the fake releases into the given folder, or into a new temporary one. */
function stage(context, releases, limit, existingOutputDirectory) {
  let outputDirectory = existingOutputDirectory;
  if (outputDirectory === undefined) {
    const directory = createTemporaryDirectory(context);
    outputDirectory = join(directory, "releases");
  }
  context.mock.method(console, "warn", () => {});
  const { gh, calls } = createFakeGh(releases);
  const stagedTags = stageReleases({ limit, outputDirectory, gh });
  return { stagedTags, outputDirectory, calls };
}

/** Reads the staged schema of a release. */
function readStagedSchema(outputDirectory, tag) {
  const schemaPath = join(outputDirectory, tag, "schema.graphql");
  return readFileSync(schemaPath, "utf8");
}

/** Tells if a release folder exists in the output folder. */
function hasReleaseDirectory(outputDirectory, tag) {
  const releaseDirectory = join(outputDirectory, tag);
  return existsSync(releaseDirectory);
}

test("accepts a limit from 1 to 50", () => {
  const limits = ["1", "10", "50"].map(parseLimit);
  assert.deepEqual(limits, [1, 10, 50]);
});

test("rejects a limit that is not a whole number from 1 to 50", () => {
  const limits = [undefined, "", "0", "51", "-1", "1.5", "all"].map(parseLimit);
  assert.deepEqual(limits, [null, null, null, null, null, null, null]);
});

test("picks the plain schema when a metadata file is next to it", () => {
  const assetName = pickSchemaAsset(["metadata.yaml", "schema.graphql", "release.tar.gz"]);
  assert.equal(assetName, "schema.graphql");
});

test("picks release.tar.gz when the plain schema has no metadata file", () => {
  const assetName = pickSchemaAsset(["schema.graphql", "release.tar.gz", "other.zip"]);
  assert.equal(assetName, "release.tar.gz");
});

test("picks the only archive", () => {
  const assetName = pickSchemaAsset(["notes.txt", "model.zip"]);
  assert.equal(assetName, "model.zip");
});

test("picks nothing when there are two archives", () => {
  const assetName = pickSchemaAsset(["first.tar", "second.tgz"]);
  assert.equal(assetName, null);
});

test("picks nothing when no asset holds a schema", () => {
  const assetName = pickSchemaAsset(["notes.txt"]);
  assert.equal(assetName, null);
});

test("finds a nested schema in an archive", (context) => {
  const directory = createTemporaryDirectory(context);
  writeFiles(directory, { "metadata.yaml": "", "spec/schema.graphql": "type A { id: ID }" });
  const schemaPath = findArchiveSchema(directory);
  const expectedPath = join(directory, "spec", "schema.graphql");
  assert.equal(schemaPath, expectedPath);
});

test("rejects an archive without a top-level metadata file", (context) => {
  const directory = createTemporaryDirectory(context);
  writeFiles(directory, { "spec/metadata.yaml": "", "schema.graphql": "type A { id: ID }" });
  assert.throws(() => findArchiveSchema(directory), { code: "MISSING_METADATA" });
});

test("rejects an archive with two schemas", (context) => {
  const directory = createTemporaryDirectory(context);
  writeFiles(directory, { "metadata.yaml": "", "schema.graphql": "", "spec/schema.graphql": "" });
  assert.throws(() => findArchiveSchema(directory), { code: "SCHEMA_COUNT" });
});

test("skips releases without a schema or with a slash in the tag", (context) => {
  const releases = [
    { tag: "v4", assets: { "notes.txt": "" } },
    { tag: "v3", assets: { "metadata.yaml": "", "schema.graphql": "type V3 { id: ID }" } },
    { tag: "release/v2", assets: { "metadata.yaml": "", "schema.graphql": "type V2 { id: ID }" } },
    { tag: "v1", assets: { "metadata.yaml": "", "schema.graphql": "type V1 { id: ID }" } },
  ];
  const { stagedTags, outputDirectory } = stage(context, releases, 2);
  const releasesListPath = join(outputDirectory, "releases.json");
  const releasesList = readFileSync(releasesListPath, "utf8");
  const listedTags = JSON.parse(releasesList);
  const newestSchema = readStagedSchema(outputDirectory, "v3");
  const oldestSchema = readStagedSchema(outputDirectory, "v1");
  assert.deepEqual(stagedTags, ["v3", "v1"]);
  assert.deepEqual(listedTags, ["v3", "v1"]);
  assert.equal(newestSchema, "type V3 { id: ID }");
  assert.equal(oldestSchema, "type V1 { id: ID }");
});

test("skips a release whose download fails", (context) => {
  const releases = [
    { tag: "v2", assets: { "metadata.yaml": "", "schema.graphql": "" }, failDownload: true },
    { tag: "v1", assets: { "metadata.yaml": "", "schema.graphql": "" } },
  ];
  const { stagedTags, outputDirectory } = stage(context, releases, 2);
  const hasFailedRelease = hasReleaseDirectory(outputDirectory, "v2");
  assert.deepEqual(stagedTags, ["v1"]);
  assert.equal(hasFailedRelease, false);
});

test("stops when the limit is reached", (context) => {
  const releases = [
    { tag: "v3", assets: { "metadata.yaml": "", "schema.graphql": "" } },
    { tag: "v1", assets: { "metadata.yaml": "", "schema.graphql": "" } },
  ];
  const { stagedTags, calls } = stage(context, releases, 1);
  const readOlderRelease = calls.some((args) => args.includes("v1"));
  assert.deepEqual(stagedTags, ["v3"]);
  assert.equal(readOlderRelease, false);
});

test("stages every release when the limit is above the list", (context) => {
  const releases = [
    { tag: "v2", assets: { "metadata.yaml": "", "schema.graphql": "" } },
    { tag: "v1", assets: { "metadata.yaml": "", "schema.graphql": "" } },
  ];
  const { stagedTags } = stage(context, releases, 5);
  assert.deepEqual(stagedTags, ["v2", "v1"]);
});

test("stages the schema from an archive release", (context) => {
  const archive = createTarGz(context, { "metadata.yaml": "", "model/schema.graphql": "type Archived { id: ID }" });
  const releases = [{ tag: "v1", assets: { "release.tar.gz": archive } }];
  const { stagedTags, outputDirectory } = stage(context, releases, 1);
  const stagedSchema = readStagedSchema(outputDirectory, "v1");
  assert.deepEqual(stagedTags, ["v1"]);
  assert.equal(stagedSchema, "type Archived { id: ID }");
});

test("removes the old output folder", (context) => {
  const directory = createTemporaryDirectory(context);
  const outputDirectory = join(directory, "releases");
  writeFiles(outputDirectory, { "old/schema.graphql": "" });
  stage(context, [], 1, outputDirectory);
  const hasOldRelease = hasReleaseDirectory(outputDirectory, "old");
  assert.equal(hasOldRelease, false);
});
