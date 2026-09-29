// Copied after install rather than committed, so it matches the installed sql.js.
const { copyFileSync, mkdirSync } = require("node:fs");
const { dirname, join } = require("node:path");

const source = require.resolve("sql.js/dist/sql-wasm-browser.wasm");
const destination = join(__dirname, "..", "static", "sql-wasm.wasm");

mkdirSync(dirname(destination), { recursive: true });
copyFileSync(source, destination);
console.log(`Copied ${source} -> ${destination}`);
