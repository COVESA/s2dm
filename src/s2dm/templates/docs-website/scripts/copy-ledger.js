// Staged in `../dist/` like the composed schema, and optional.
const { copyFileSync, existsSync, mkdirSync, rmSync } = require("node:fs");
const { join } = require("node:path");

const source = join(__dirname, "..", "..", "dist", "ledger.db");
const destination = join(__dirname, "..", "static", "ledger.db");

if (!existsSync(source)) {
	rmSync(destination, { force: true });
	console.log(`No ledger at ${source}; the Ledger page will report it missing.`);
	process.exit(0);
}

mkdirSync(join(__dirname, "..", "static"), { recursive: true });
copyFileSync(source, destination);
console.log(`Copied ${source} -> ${destination}`);
