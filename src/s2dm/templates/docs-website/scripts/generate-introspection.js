const { buildSchema, introspectionFromSchema } = require("graphql");
const fs = require("fs");
const path = require("path");

const schemaPath = path.resolve(__dirname, "../../dist/model.graphql");

if (!fs.existsSync(schemaPath)) {
  console.error(`Error: could not read ${schemaPath}`);
  console.error('Make sure you have composed the model into an stand-alone valid GraphQL schema file (e.g., via `s2dm compose`) before generating the introspection.json file.');
  console.error('Make sure the `generate-instrospection.js` script has the correct path to the composed schema file.');
  process.exit(1);
}

const sdl = fs.readFileSync(schemaPath, "utf8");
const schema = buildSchema(sdl);
fs.writeFileSync(
  path.resolve(__dirname, "../static/introspection.json"),
  JSON.stringify({ data: introspectionFromSchema(schema) }),
);
console.log("introspection.json written.");
